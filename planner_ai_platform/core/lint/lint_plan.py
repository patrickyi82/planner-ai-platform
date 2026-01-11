from __future__ import annotations

from collections import Counter, defaultdict, deque
from typing import Any, Optional

from planner_ai_platform.core.errors import PlanValidationError


# Standard Delivery Framework (SDF) v0 lint rules (Phase 2)
# We start small but meaningful:
# - L_DUPLICATE_ID: duplicate node IDs
# - L_EMPTY_DEFINITION_OF_DONE: tasks/checks must have at least 1 DoD item
# - L_TASK_MISSING_OWNER: tasks must specify a non-empty owner
# - L_UNREACHABLE_NODE: node not reachable from selected roots (root_ids or inferred roots)
# - L_CYCLE_DETECTED: dependency cycle exists


def lint_plan(plan: dict[str, Any]) -> list[PlanValidationError]:
    """Lint a plan.

    Lint runs *in addition to* schema validation. It is allowed to operate on
    partially-invalid inputs (best effort) and enforce stronger standards.

    The CLI prints lint + validation errors together.
    """

    file = _cast_optional_str(plan.get("__file__"))

    nodes = plan.get("nodes")
    if not isinstance(nodes, list):
        # Let validator handle shape.
        return []

    # Index nodes (best effort).
    id_to_index: dict[str, int] = {}
    id_to_raw: dict[str, dict[str, Any]] = {}
    ids: list[str] = []

    for i, raw in enumerate(nodes):
        if not isinstance(raw, dict):
            continue
        nid = raw.get("id")
        if not isinstance(nid, str):
            continue
        ids.append(nid)
        id_to_index.setdefault(nid, i)
        id_to_raw.setdefault(nid, raw)

    errors: list[PlanValidationError] = []

    # Rule: duplicate IDs
    counts = Counter(ids)
    dupes = {k: v for k, v in counts.items() if v > 1}
    if dupes:
        seen: set[str] = set()
        for i, raw in enumerate(nodes):
            if not isinstance(raw, dict):
                continue
            nid = raw.get("id")
            if not isinstance(nid, str) or nid not in dupes:
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

    # Extract deps/types (best effort).
    id_to_deps: dict[str, list[str]] = {}
    id_to_type: dict[str, str] = {}

    for nid, raw in id_to_raw.items():
        ntype = raw.get("type")
        if isinstance(ntype, str):
            id_to_type[nid] = ntype

        deps_raw = raw.get("depends_on")
        deps: list[str] = []
        if isinstance(deps_raw, list):
            deps = [d for d in deps_raw if isinstance(d, str)]
        id_to_deps[nid] = deps

    # Rule: tasks/checks must have non-empty DoD
    for nid, raw in id_to_raw.items():
        ntype = id_to_type.get(nid, "")
        if ntype not in {"task", "check"}:
            continue
        dod = raw.get("definition_of_done")
        if isinstance(dod, list) and len(dod) == 0:
            errors.append(
                PlanValidationError(
                    code="L_EMPTY_DEFINITION_OF_DONE",
                    message=f"{ntype} must have at least 1 definition_of_done item",
                    file=file,
                    path=f"nodes[{id_to_index.get(nid, 0)}].definition_of_done",
                )
            )

    # Rule: tasks must have owner
    for nid, raw in id_to_raw.items():
        if id_to_type.get(nid) != "task":
            continue
        owner = raw.get("owner")
        if not isinstance(owner, str) or not owner.strip():
            errors.append(
                PlanValidationError(
                    code="L_TASK_MISSING_OWNER",
                    message="task must specify a non-empty owner",
                    file=file,
                    path=f"nodes[{id_to_index.get(nid, 0)}].owner",
                )
            )

    # Rule: unreachable nodes (only if we can infer roots)
    roots = _select_roots(plan, id_to_raw, id_to_deps)
    if roots:
        reachable = _reachable_from_roots(roots, id_to_deps)
        for nid in sorted(set(id_to_raw.keys()) - reachable):
            errors.append(
                PlanValidationError(
                    code="L_UNREACHABLE_NODE",
                    message=f"node is not reachable from roots: {sorted(roots)}",
                    file=file,
                    path=f"nodes[{id_to_index.get(nid, 0)}].id",
                )
            )

    # Rule: cycle detection
    for nid, msg in _detect_cycles(id_to_deps):
        errors.append(
            PlanValidationError(
                code="L_CYCLE_DETECTED",
                message=msg,
                file=file,
                path=f"nodes[{id_to_index.get(nid, 0)}].depends_on",
            )
        )

    return _sorted(errors)


def _select_roots(
    plan: dict[str, Any],
    id_to_raw: dict[str, dict[str, Any]],
    id_to_deps: dict[str, list[str]],
) -> list[str]:
    root_ids = plan.get("root_ids")
    if isinstance(root_ids, list) and all(isinstance(x, str) for x in root_ids):
        out: list[str] = []
        for rid in root_ids:
            if rid in id_to_raw and len(id_to_deps.get(rid, [])) == 0:
                out.append(rid)
        return out

    return [nid for nid, deps in id_to_deps.items() if len(deps) == 0]


def _reachable_from_roots(roots: list[str], id_to_deps: dict[str, list[str]]) -> set[str]:
    # dep -> list of nodes that depend on it
    dependents: dict[str, list[str]] = defaultdict(list)
    for nid, deps in id_to_deps.items():
        for dep in deps:
            if dep in id_to_deps:
                dependents[dep].append(nid)

    q: deque[str] = deque(roots)
    seen: set[str] = set()
    while q:
        cur = q.popleft()
        if cur in seen:
            continue
        seen.add(cur)
        for nxt in dependents.get(cur, []):
            if nxt not in seen:
                q.append(nxt)
    return seen


def _detect_cycles(id_to_deps: dict[str, list[str]]) -> list[tuple[str, str]]:
    WHITE, GRAY, BLACK = 0, 1, 2
    state: dict[str, int] = {nid: WHITE for nid in id_to_deps.keys()}
    stack: list[str] = []
    emitted: set[str] = set()
    out: list[tuple[str, str]] = []

    def dfs(u: str) -> None:
        state[u] = GRAY
        stack.append(u)
        for v in id_to_deps.get(u, []):
            if v not in state:
                continue
            if state[v] == GRAY:
                # cycle: v ... u -> v
                try:
                    idx = stack.index(v)
                except ValueError:
                    idx = 0
                cycle = stack[idx:] + [v]
                key = "->".join(cycle)
                if key not in emitted:
                    emitted.add(key)
                    out.append((u, "dependency cycle detected: " + " -> ".join(cycle)))
            elif state[v] == WHITE:
                dfs(v)
        stack.pop()
        state[u] = BLACK

    for nid in list(state.keys()):
        if state[nid] == WHITE:
            dfs(nid)

    return out


def _sorted(errors: list[PlanValidationError]) -> list[PlanValidationError]:
    return sorted(errors, key=lambda e: (e.file or "", e.path or "", e.code))


def _cast_optional_str(v: Any) -> Optional[str]:
    return v if isinstance(v, str) else None
