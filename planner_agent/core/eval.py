from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from planner_agent.core.orchestrator import SliceSpec, run_slice
from planner_agent.core.repo import find_repo_root
from planner_agent.core.worktree import ensure_clean_git, temp_worktree


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    goal: str
    acceptance: list[str]
    tags: list[str]


def _case_from_obj(obj: dict[str, Any], fallback_id: str) -> EvalCase:
    goal = str(obj.get("goal", "")).strip()
    if not goal:
        raise ValueError(f"Eval case missing 'goal' ({fallback_id})")

    acc = obj.get("acceptance") or []
    if not isinstance(acc, list):
        acc = [str(acc)]

    tags = obj.get("tags") or []
    if not isinstance(tags, list):
        tags = [str(tags)]

    case_id = str(obj.get("id") or fallback_id)
    return EvalCase(
        case_id=case_id,
        goal=goal,
        acceptance=[str(a) for a in acc],
        tags=[str(t) for t in tags],
    )


def load_suite(path: Path) -> list[EvalCase]:
    """Load a suite from a YAML file or directory.

    - Directory: *.yaml/*.yml files, each can be mapping (one case) or list (many)
    - File: mapping (one case) or list (many)
    """
    p = Path(path)
    if p.is_dir():
        files = sorted(list(p.glob("*.yaml")) + list(p.glob("*.yml")))
        cases: list[EvalCase] = []
        for f in files:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        cases.append(_case_from_obj(item, f"{f.stem}:{i}"))
            elif isinstance(data, dict):
                cases.append(_case_from_obj(data, f.stem))
        return cases

    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [
            _case_from_obj(item, f"case:{i}")
            for i, item in enumerate(data)
            if isinstance(item, dict)
        ]
    if isinstance(data, dict):
        return [_case_from_obj(data, p.stem)]
    raise ValueError(f"Unsupported suite format: {p}")


def _iter_models(models: Iterable[str]) -> list[str]:
    out = [str(m).strip() for m in models if str(m).strip()]
    if not out:
        raise ValueError("No models provided")
    return out


def run_eval(
    *,
    suite_path: Path,
    models: Iterable[str],
    runs: int,
    workers: int,
    max_fix_rounds: int,
    out_jsonl: Path,
    allow_dirty: bool = False,
    use_worktrees: bool = True,
    keep_worktrees: bool = False,
) -> dict[str, Any]:
    repo_root = find_repo_root()

    # In unit tests (or if you want), avoid worktrees.
    if os.environ.get("PYTEST_CURRENT_TEST"):
        use_worktrees = False

    # If we use worktrees, we evaluate from HEAD in an isolated checkout,
    # so uncommitted changes in the main working tree are irrelevant (but also
    # won't be included in the eval). If you want to include local changes,
    # run with --no-worktrees and optionally --allow-dirty.
    if (not use_worktrees) and (not allow_dirty):
        ensure_clean_git(repo_root)

    cases = load_suite(Path(suite_path))
    if not cases:
        raise ValueError(f"No cases found in suite: {suite_path}")

    models_list = _iter_models(models)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    totals: dict[str, dict[str, float]] = {
        m: {
            "runs": 0.0,
            "ok": 0.0,
            "seconds": 0.0,
            "fixes": 0.0,
            "calls": 0.0,
            "in_tokens": 0.0,
            "out_tokens": 0.0,
        }
        for m in models_list
    }

    with out_jsonl.open("w", encoding="utf-8") as f:
        for model in models_list:
            for case in cases:
                for r in range(max(1, runs)):
                    started = time.time()
                    spec = SliceSpec(goal=case.goal, acceptance=case.acceptance)

                    if use_worktrees:
                        with temp_worktree(Path(repo_root), keep=keep_worktrees) as wt:
                            rr = _run_one(wt.path, spec, model, workers, max_fix_rounds)
                    else:
                        rr = _run_one(Path(repo_root), spec, model, workers, max_fix_rounds)

                    elapsed = time.time() - started
                    fixes = sum(1 for p in rr.applied_patches if p.role == "fixer")

                    record = {
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "model": model,
                        "case_id": case.case_id,
                        "goal": case.goal,
                        "tags": case.tags,
                        "run_index": r,
                        "ok": rr.ok,
                        "seconds": elapsed,
                        "patches": len(rr.applied_patches),
                        "fix_patches": fixes,
                        "gates": [
                            {"name": g.name, "ok": g.ok, "exit_code": g.exit_code} for g in rr.gates
                        ],
                        "llm": {
                            "calls": getattr(rr, "llm_calls", 0),
                            "input_tokens": getattr(rr, "llm_input_tokens", 0),
                            "output_tokens": getattr(rr, "llm_output_tokens", 0),
                            "models_used": getattr(rr, "models_used", {}),
                        },
                    }
                    f.write(json.dumps(record) + "\n")

                    t = totals[model]
                    t["runs"] += 1.0
                    t["ok"] += 1.0 if rr.ok else 0.0
                    t["seconds"] += float(elapsed)
                    t["fixes"] += float(fixes)
                    t["calls"] += float(getattr(rr, "llm_calls", 0))
                    t["in_tokens"] += float(getattr(rr, "llm_input_tokens", 0))
                    t["out_tokens"] += float(getattr(rr, "llm_output_tokens", 0))

    summary: dict[str, Any] = {}
    for model, t in totals.items():
        runs_n = max(1.0, t["runs"])
        summary[model] = {
            "runs": int(t["runs"]),
            "success_rate": t["ok"] / runs_n,
            "avg_seconds": t["seconds"] / runs_n,
            "avg_fix_patches": t["fixes"] / runs_n,
            "avg_llm_calls": t["calls"] / runs_n,
            "avg_input_tokens": t["in_tokens"] / runs_n,
            "avg_output_tokens": t["out_tokens"] / runs_n,
        }

    return {"cases": len(cases), "models": models_list, "summary": summary, "out": str(out_jsonl)}


def _run_one(repo_root: Path, spec: SliceSpec, model: str, workers: int, max_fix_rounds: int):
    import asyncio

    return asyncio.run(
        run_slice(repo_root, spec, workers=workers, max_fix_rounds=max_fix_rounds, model=model)
    )
