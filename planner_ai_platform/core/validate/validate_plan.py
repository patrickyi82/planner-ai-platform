from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Optional, cast

from planner_ai_platform.core.errors import PlanValidationError
from planner_ai_platform.core.model import NodeType, PlanGraph, PlanNode


ALLOWED_NODE_TYPES: set[str] = {"outcome", "deliverable", "milestone", "task", "check"}


def _is_list_of_str(v: Any) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) for x in v)


def _is_list_of_str_or_empty(v: Any) -> bool:
    return v == [] or _is_list_of_str(v)


def validate_plan(plan: dict[str, Any]) -> tuple[Optional[PlanGraph], list[PlanValidationError]]:
    """Validate plan schema v0-ish.

    Returns (graph, errors). Graph is None when errors exist.
    """

    file = cast(Optional[str], plan.get("__file__"))
    errors: list[PlanValidationError] = []

    schema_version = plan.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version.strip():
        errors.append(
            PlanValidationError(
                code="E_REQUIRED_FIELD",
                message="schema_version is required and must be a non-empty string",
                file=file,
                path="schema_version",
            )
        )

    nodes = plan.get("nodes")
    if not isinstance(nodes, list):
        errors.append(
            PlanValidationError(
                code="E_REQUIRED_FIELD",
                message="nodes is required and must be an array",
                file=file,
                path="nodes",
            )
        )
        return None, _sorted(errors)

    # Validate each node and build map.
    nodes_by_id: dict[str, PlanNode] = {}
    raw_nodes_by_id: dict[str, dict[str, Any]] = {}

    for i, raw in enumerate(nodes):
        node_path = f"nodes[{i}]"
        if not isinstance(raw, dict):
            errors.append(
                PlanValidationError(
                    code="E_INVALID_TYPE",
                    message="node must be an object",
                    file=file,
                    path=node_path,
                )
            )
            continue

        # Required fields.
        nid = raw.get("id")
        if not isinstance(nid, str) or not nid.strip():
            errors.append(
                PlanValidationError(
                    code="E_REQUIRED_FIELD",
                    message="id is required and must be a non-empty string",
                    file=file,
                    path=f"{node_path}.id",
                )
            )
            continue

        if nid in raw_nodes_by_id:
            errors.append(
                PlanValidationError(
                    code="E_DUPLICATE_ID",
                    message=f"duplicate node id: {nid}",
                    file=file,
                    path=f"{node_path}.id",
                )
            )
            continue

        ntype = raw.get("type")
        if not isinstance(ntype, str) or ntype not in ALLOWED_NODE_TYPES:
            errors.append(
                PlanValidationError(
                    code="E_INVALID_ENUM",
                    message=f"type must be one of {sorted(ALLOWED_NODE_TYPES)}",
                    file=file,
                    path=f"{node_path}.type",
                )
            )
            continue

        title = raw.get("title")
        if not isinstance(title, str) or not title.strip():
            errors.append(
                PlanValidationError(
                    code="E_REQUIRED_FIELD",
                    message="title is required and must be a non-empty string",
                    file=file,
                    path=f"{node_path}.title",
                )
            )
            continue

        dod = raw.get("definition_of_done")
        if not _is_list_of_str(dod):
            errors.append(
                PlanValidationError(
                    code="E_INVALID_TYPE",
                    message="definition_of_done must be an array of strings",
                    file=file,
                    path=f"{node_path}.definition_of_done",
                )
            )
            continue

        deps = raw.get("depends_on")
        if not _is_list_of_str_or_empty(deps):
            errors.append(
                PlanValidationError(
                    code="E_INVALID_TYPE",
                    message="depends_on must be an array of strings",
                    file=file,
                    path=f"{node_path}.depends_on",
                )
            )
            continue
        deps = cast(list[str], deps)

        owner = raw.get("owner")
        if owner is not None and not isinstance(owner, str):
            errors.append(
                PlanValidationError(
                    code="E_INVALID_TYPE",
                    message="owner must be a string",
                    file=file,
                    path=f"{node_path}.owner",
                )
            )

        estimate_hours = raw.get("estimate_hours")
        if estimate_hours is not None and not isinstance(estimate_hours, (int, float)):
            errors.append(
                PlanValidationError(
                    code="E_INVALID_TYPE",
                    message="estimate_hours must be a number",
                    file=file,
                    path=f"{node_path}.estimate_hours",
                )
            )

        priority = raw.get("priority")
        if priority is not None and not isinstance(priority, int):
            errors.append(
                PlanValidationError(
                    code="E_INVALID_TYPE",
                    message="priority must be an integer",
                    file=file,
                    path=f"{node_path}.priority",
                )
            )

        raw_nodes_by_id[nid] = raw
        nodes_by_id[nid] = PlanNode(
            id=nid,
            type=cast(NodeType, ntype),
            title=title,
            definition_of_done=cast(list[str], dod),
            depends_on=deps,
            owner=cast(Optional[str], owner),
            estimate_hours=cast(Optional[float], estimate_hours),
            priority=cast(Optional[int], priority),
        )

    # Referential integrity checks.
    if raw_nodes_by_id:
        all_ids = set(raw_nodes_by_id.keys())
        for nid, raw in raw_nodes_by_id.items():
            deps = raw.get("depends_on") or []
            for di, dep in enumerate(deps):
                if dep not in all_ids:
                    errors.append(
                        PlanValidationError(
                            code="E_UNKNOWN_DEPENDENCY",
                            message=f"depends_on references unknown id: {dep}",
                            file=file,
                            path=f"nodes[{_index_of_node(nodes, nid)}].depends_on[{di}]",
                        )
                    )

    # Root detection rules.
    root_ids = plan.get("root_ids")
    roots: list[str] = []
    if root_ids is None:
        roots = [nid for nid, n in nodes_by_id.items() if len(n.depends_on) == 0]
        if not roots:
            errors.append(
                PlanValidationError(
                    code="E_NO_ROOTS",
                    message="no root nodes found (a root must have depends_on: [])",
                    file=file,
                    path="root_ids",
                )
            )
    else:
        if not _is_list_of_str(root_ids):
            errors.append(
                PlanValidationError(
                    code="E_INVALID_TYPE",
                    message="root_ids must be an array of strings",
                    file=file,
                    path="root_ids",
                )
            )
        else:
            root_ids = cast(list[str], root_ids)
            for ri, rid in enumerate(root_ids):
                if rid not in nodes_by_id:
                    errors.append(
                        PlanValidationError(
                            code="E_UNKNOWN_ROOT",
                            message=f"root_ids references unknown id: {rid}",
                            file=file,
                            path=f"root_ids[{ri}]",
                        )
                    )
                else:
                    if nodes_by_id[rid].depends_on:
                        errors.append(
                            PlanValidationError(
                                code="E_ROOT_HAS_DEPENDENCIES",
                                message=f"root node must have depends_on: [], but {rid} has dependencies",
                                file=file,
                                path=f"root_ids[{ri}]",
                            )
                        )
                    else:
                        roots.append(rid)
            if not roots and not any(e.code in {"E_INVALID_TYPE"} for e in errors):
                errors.append(
                    PlanValidationError(
                        code="E_NO_ROOTS",
                        message="root_ids did not yield any valid roots",
                        file=file,
                        path="root_ids",
                    )
                )

    if errors:
        return None, _sorted(errors)

    edges: list[tuple[str, str]] = []
    for nid, n in nodes_by_id.items():
        for dep in n.depends_on:
            edges.append((nid, dep))

    graph = PlanGraph(
        schema_version=cast(str, schema_version),
        nodes_by_id=nodes_by_id,
        edges=edges,
        roots=sorted(roots),
    )
    return graph, []


def summarize_plan(graph: PlanGraph) -> str:
    counts = Counter([n.type for n in graph.nodes_by_id.values()])
    ordered_types: list[str] = ["outcome", "deliverable", "milestone", "task", "check"]
    parts = [f"{t}={counts.get(t, 0)}" for t in ordered_types]
    return (
        f"OK: {len(graph.nodes_by_id)} nodes ("
        + ", ".join(parts)
        + ")\nRoots: "
        + ", ".join(graph.roots)
    )


def _sorted(errors: Iterable[PlanValidationError]) -> list[PlanValidationError]:
    return sorted(
        list(errors),
        key=lambda e: (
            e.file or "",
            e.path or "",
            e.code,
        ),
    )


def _index_of_node(nodes: list[Any], node_id: str) -> int:
    for i, n in enumerate(nodes):
        if isinstance(n, dict) and n.get("id") == node_id:
            return i
    return 0
