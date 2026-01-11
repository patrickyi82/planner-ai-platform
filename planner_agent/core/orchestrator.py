from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from planner_agent.core.apply import apply_patch
from planner_agent.core.contracts import FileEdit, Patch, RunResult
import os

from planner_agent.core.gates import DEFAULT_GATES, Gate, run_gates
from planner_agent.core.llm import LLMClient
from planner_agent.core.prompts import DEFAULT_PROMPTS
from planner_agent.core.repomap import build_repomap
from planner_agent.core.repo import RepoSnapshot


PATCH_SCHEMA: dict[str, Any] = {
    "name": "Patch",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "summary": {"type": "string"},
            "confidence": {"type": "number"},
            "edits": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        "required": ["summary", "edits", "confidence"],
    },
}


@dataclass(frozen=True)
class SliceSpec:
    goal: str
    # optional: additional constraints and acceptance criteria
    acceptance: list[str]


def default_slice(goal: str) -> SliceSpec:
    return SliceSpec(
        goal=goal,
        acceptance=[
            "All tests pass (pytest)",
            "planner validate examples/basic-plan.yaml passes",
            "Changes are minimal and consistent with existing conventions",
        ],
    )


def _effective_gates() -> list[Gate]:
    gates = list(DEFAULT_GATES)
    # Avoid running pytest *inside* pytest (recursive test runner can hang).
    if os.environ.get("PYTEST_CURRENT_TEST"):
        gates = [g for g in gates if g.name != "pytest"]
    return gates


async def run_slice(repo_root: Path, spec: SliceSpec, workers: int = 3, max_fix_rounds: int = 3, model: str | None = None) -> RunResult:
    snapshot = RepoSnapshot(root=repo_root)
    repomap = build_repomap(snapshot).to_text()

    llm = LLMClient(model=model)
    prompts = DEFAULT_PROMPTS

    sem = asyncio.Semaphore(max(1, workers))

    async def ask(role: str, system: str, user: str) -> Patch:
        async with sem:
            resp = await asyncio.to_thread(llm.respond, system, user, PATCH_SCHEMA)
        try:
            data = json.loads(resp.text)
        except Exception:
            # fallback: treat as no-op
            data = {"summary": "invalid JSON from LLM", "edits": [], "confidence": 0.0}

        edits = [FileEdit(path=e["path"], content=e["content"]) for e in data.get("edits", [])]
        return Patch(
            edits=edits,
            summary=str(data.get("summary", "")),
            role=role,  # type: ignore
            confidence=float(data.get("confidence", 0.5)),
        )

    base_user = (
        f"Goal: {spec.goal}\n\n"
        f"Acceptance criteria:\n" + "\n".join([f"- {a}" for a in spec.acceptance]) + "\n\n" + repomap
    )

    # Phase 1: propose patches in parallel (thinking).
    tasks = [
        ask("coder", prompts.coder, base_user),
        ask("tester", prompts.tester, base_user),
        ask("docs", prompts.docs, base_user),
    ]

    proposed = await asyncio.gather(*tasks)

    applied: list[Patch] = []

    # Phase 2: apply patches serially (writing).
    for patch in proposed:
        if not patch.edits:
            continue
        apply_patch(repo_root, patch)
        applied.append(patch)

        gates = run_gates(repo_root, _effective_gates())
        if not gates[-1].ok:
            # attempt fix loops
            fix_round = 0
            while fix_round < max_fix_rounds and (not gates[-1].ok):
                fix_round += 1
                failure_text = f"Gate failed: {gates[-1].name}\nCommand: {gates[-1].command}\nOutput:\n{gates[-1].output}"
                fix_user = base_user + "\n\n" + failure_text
                fix_patch = await ask("fixer", prompts.fixer, fix_user)
                if not fix_patch.edits:
                    break
                apply_patch(repo_root, fix_patch)
                applied.append(fix_patch)
                gates = run_gates(repo_root, _effective_gates())

            return RunResult(
                ok=gates[-1].ok,
                applied_patches=applied,
                gates=gates,
                model=llm.model,
                llm_calls=llm.calls,
                llm_input_tokens=llm.input_tokens,
                llm_output_tokens=llm.output_tokens,
            )

    gates = run_gates(repo_root, _effective_gates())
    return RunResult(
        ok=gates[-1].ok,
        applied_patches=applied,
        gates=gates,
        model=llm.model,
        llm_calls=llm.calls,
        llm_input_tokens=llm.input_tokens,
        llm_output_tokens=llm.output_tokens,
    )

