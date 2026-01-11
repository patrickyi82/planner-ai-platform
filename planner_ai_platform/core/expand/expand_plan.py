from __future__ import annotations

from typing import Any, Literal

import yaml

from planner_ai_platform.core.expand.template_config import DEFAULT_TEMPLATES

ExpandMode = Literal["append", "merge"]


def expand_plan_dict(
    plan: dict[str, Any],
    *,
    outcome_root_ids: list[str],
    template: str = "simple",
    templates: dict[str, list[str]] | None = None,
    mode: ExpandMode = "append",
) -> dict[str, Any]:
    """Return a new expanded plan dict.

    Phase 3 is deterministic (no AI). Two behaviors are supported:

    - append (default): always add a new deliverable + task chain, allocating unique IDs.
    - merge: be idempotent by reusing previously generated nodes when they already exist.

    merge mode never edits existing nodes; it only adds missing ones.
    """
    schema_version = plan.get("schema_version")
    nodes = plan.get("nodes")

    out: dict[str, Any] = {"schema_version": schema_version, "nodes": []}
    if "root_ids" in plan:
        out["root_ids"] = plan.get("root_ids")

    if not isinstance(nodes, list):
        out["nodes"] = nodes
        return out

    tpl_map = templates or DEFAULT_TEMPLATES
    task_titles = tpl_map.get(template, tpl_map.get("simple", DEFAULT_TEMPLATES["simple"]))

    existing_ids = _collect_existing_ids(nodes)
    new_nodes: list[dict[str, Any]] = []

    deliverables_by_key, tasks_by_key = _index_existing(nodes)

    for out_id in outcome_root_ids:
        deliverable_title = f"Deliver: {out_id}"

        # Deliverable selection/creation
        if mode == "merge":
            del_candidates = deliverables_by_key.get((deliverable_title, out_id), [])
            if del_candidates:
                del_id = sorted(del_candidates)[0]
            else:
                del_base = f"DEL-{out_id}-01"
                del_id = _unique_id(del_base, existing_ids)
                existing_ids.add(del_id)
                new_nodes.append(
                    {
                        "id": del_id,
                        "type": "deliverable",
                        "title": deliverable_title,
                        "definition_of_done": ["Implementation complete", "Reviewed and accepted"],
                        "depends_on": [out_id],
                    }
                )
                deliverables_by_key.setdefault((deliverable_title, out_id), []).append(del_id)
        else:
            del_base = f"DEL-{out_id}-01"
            del_id = _unique_id(del_base, existing_ids)
            existing_ids.add(del_id)
            new_nodes.append(
                {
                    "id": del_id,
                    "type": "deliverable",
                    "title": deliverable_title,
                    "definition_of_done": ["Implementation complete", "Reviewed and accepted"],
                    "depends_on": [out_id],
                }
            )

        # Tasks under deliverable
        prev_task_id: str | None = None
        for i, title in enumerate(task_titles, start=1):
            task_title = f"{title}: {out_id}"

            if mode == "merge":
                t_candidates = tasks_by_key.get((task_title, del_id), [])
                if t_candidates:
                    t_id = sorted(t_candidates)[0]
                    prev_task_id = t_id
                    continue

            t_base = f"TSK-{out_id}-{i:02d}"
            t_id = _unique_id(t_base, existing_ids)
            existing_ids.add(t_id)

            deps = [del_id]
            if prev_task_id is not None:
                deps.append(prev_task_id)

            new_nodes.append(
                {
                    "id": t_id,
                    "type": "task",
                    "title": task_title,
                    "definition_of_done": [f"{title} complete"],
                    "depends_on": deps,
                    "owner": "auto",
                    "estimate_hours": 1,
                }
            )

            tasks_by_key.setdefault((task_title, del_id), []).append(t_id)
            prev_task_id = t_id

    out["nodes"] = list(nodes) + new_nodes
    return out


def dump_plan_yaml(plan: dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(plan, f, sort_keys=False, default_flow_style=False, allow_unicode=True)


def _collect_existing_ids(nodes: list[Any]) -> set[str]:
    ids: set[str] = set()
    for raw in nodes:
        if isinstance(raw, dict):
            nid = raw.get("id")
            if isinstance(nid, str):
                ids.add(nid)
    return ids


def _index_existing(nodes: list[Any]) -> tuple[dict[tuple[str, str], list[str]], dict[tuple[str, str], list[str]]]:
    """Build lookup tables used by merge mode.

    deliverables_by_key: (deliverable_title, out_id) -> [deliverable_id...]
      matches title='Deliver: <out_id>' and depends_on contains <out_id>.

    tasks_by_key: (task_title, deliverable_id) -> [task_id...]
      matches title='<Task>: <out_id>' and depends_on contains deliverable_id.
    """
    deliverables_by_key: dict[tuple[str, str], list[str]] = {}
    tasks_by_key: dict[tuple[str, str], list[str]] = {}

    for raw in nodes:
        if not isinstance(raw, dict):
            continue
        nid = raw.get("id")
        ntype = raw.get("type")
        title = raw.get("title")
        depends_on = raw.get("depends_on")
        if not isinstance(nid, str) or not isinstance(ntype, str) or not isinstance(title, str):
            continue
        if not isinstance(depends_on, list):
            continue

        dep_ids = [d for d in depends_on if isinstance(d, str)]

        if ntype == "deliverable":
            if title.startswith("Deliver: "):
                out_id = title.split("Deliver: ", 1)[1].strip()
                if out_id and out_id in dep_ids:
                    deliverables_by_key.setdefault((title, out_id), []).append(nid)

        elif ntype == "task":
            for d in dep_ids:
                if d.startswith("DEL-"):
                    tasks_by_key.setdefault((title, d), []).append(nid)

    return deliverables_by_key, tasks_by_key


def _unique_id(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        candidate = f"{base}-{ch}"
        if candidate not in existing:
            return candidate
    raise ValueError(f"could not allocate unique id for base={base}")
