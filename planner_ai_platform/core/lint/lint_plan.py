from __future__ import annotations

from collections import Counter
from typing import Any, Optional

from planner_ai_platform.core.errors import PlanValidationError


def lint_plan(plan: dict[str, Any]) -> list[PlanValidationError]:
    """Lint a plan.

    Phase 2 v0: start with a single rule requested by user: duplicate node IDs.

    This lint intentionally works on the *raw loaded plan* so it can report issues
    even when the plan is not yet fully valid.
    """

    file = cast_optional_str(plan.get("__file__"))

    nodes = plan.get("nodes")
    if not isinstance(nodes, list):
        # Let validator handle shape; lint doesn't duplicate.
        return []

    ids: list[str] = []
    for i, raw in enumerate(nodes):
        if isinstance(raw, dict) and isinstance(raw.get("id"), str):
            ids.append(raw["id"])

    counts = Counter(ids)
    dupes = {k: v for k, v in counts.items() if v > 1}

    errors: list[PlanValidationError] = []
    if dupes:
        # Emit one error per duplicate occurrence (after the first) to point to paths.
        seen: set[str] = set()
        for i, raw in enumerate(nodes):
            if not isinstance(raw, dict):
                continue
            nid = raw.get("id")
            if not isinstance(nid, str):
                continue
            if nid not in dupes:
                continue
            if nid not in seen:
                seen.add(nid)
                continue
            errors.append(
                PlanValidationError(
                    code="L_DUPLICATE_ID",
                    message=f"duplicate node id: {nid} (count={dupes[nid]})",
                    file=file,
                    path=f"nodes[{i}].id",
                )
            )

    return _sorted(errors)


def _sorted(errors: list[PlanValidationError]) -> list[PlanValidationError]:
    return sorted(errors, key=lambda e: (e.file or "", e.path or "", e.code))


def cast_optional_str(v: Any) -> Optional[str]:
    return v if isinstance(v, str) else None
