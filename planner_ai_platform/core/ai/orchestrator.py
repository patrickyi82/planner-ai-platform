from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from planner_ai_platform.core.ai.apply_patch import ApplyPatchResult, apply_patch
from planner_ai_platform.core.ai.contracts import EditPlan


@dataclass(frozen=True)
class GateResult:
    ok: bool
    errors: list[str]


class LLM(Protocol):
    def propose_patch(self, *, context: dict[str, Any], model: str) -> EditPlan: ...


ValidatorFn = Callable[[dict[str, Any]], GateResult]


@dataclass(frozen=True)
class AIExpandResult:
    plan: dict[str, Any]
    rounds: int
    applied: list[ApplyPatchResult]
    last_gate: GateResult


def ai_expand(
    *,
    plan: dict[str, Any],
    llm: LLM,
    model: str,
    build_context: Callable[[dict[str, Any], GateResult, int], dict[str, Any]],
    gates: ValidatorFn,
    workers: int,
    max_fix_rounds: int,
    min_changes: int = 1,
) -> AIExpandResult:
    """AI-assisted expansion loop.

    - Always attempt at least one proposal round (even if gates initially pass),
      because Phase 4 goal is expansion.
    - Require proposals to include >= min_changes edits.
    - Surface proposal errors if all workers fail.
    """

    applied: list[ApplyPatchResult] = []
    current = plan
    gate = gates(current)

    if max_fix_rounds <= 0:
        return AIExpandResult(plan=current, rounds=0, applied=applied, last_gate=gate)

    for round_idx in range(1, max_fix_rounds + 1):
        context = build_context(current, gate, round_idx)

        patches: list[EditPlan] = []
        proposal_errors: list[str] = []

        with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            futures = [
                ex.submit(llm.propose_patch, context=context, model=model)
                for _ in range(max(1, workers))
            ]
            for f in as_completed(futures):
                try:
                    patches.append(f.result())
                except Exception as e:
                    proposal_errors.append(str(e))

        if not patches:
            # Nothing usable came back; return with errors so CLI can print a meaningful reason.
            return AIExpandResult(
                plan=current,
                rounds=round_idx,
                applied=applied,
                last_gate=GateResult(
                    ok=False, errors=["LLM produced no proposals"] + proposal_errors[:5]
                ),
            )

        best_candidate: tuple[int, ApplyPatchResult, GateResult] | None = None

        for patch in patches:
            change_count = len(patch.add_nodes) + len(patch.update_nodes)
            if change_count < min_changes:
                continue

            applied_res = apply_patch(current, patch)
            gate2 = gates(applied_res.plan)

            if gate2.ok:
                applied.append(applied_res)
                return AIExpandResult(
                    plan=applied_res.plan, rounds=round_idx, applied=applied, last_gate=gate2
                )

            score = len(gate2.errors)
            if best_candidate is None or score < best_candidate[0]:
                best_candidate = (score, applied_res, gate2)

        if best_candidate is None:
            # Proposals existed but none met min_changes (or they were all empty, which shouldn't happen now).
            errs = [
                f"No proposal met min_changes={min_changes}.",
            ]
            return AIExpandResult(
                plan=current,
                rounds=round_idx,
                applied=applied,
                last_gate=GateResult(ok=False, errors=errs),
            )

        _, applied_res, gate = best_candidate
        applied.append(applied_res)
        current = applied_res.plan

    return AIExpandResult(plan=current, rounds=max_fix_rounds, applied=applied, last_gate=gate)
