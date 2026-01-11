from __future__ import annotations

from typing import Any, Literal

import yaml

from planner_ai_platform.core.expand.template_config import DEFAULT_TEMPLATES


ExpandMode = Literal["append", "merge", "reconcile"]


def expand_plan_dict(
    plan: dict[str, Any],
    *,
    outcome_root_ids: list[str],
    template: str = "simple",
    templates: dict[str, list[str]] | None = None,
    mode: ExpandMode = "append",
    reconcile_strict: bool = True,
) -> dict[str, Any]:
    """Return a new expanded plan dict.

    Phase 3 is deterministic (no AI). Behaviors:

    - append (default): always add a new deliverable + task chain, allocating unique IDs.
    - merge: idempotent by reusing previously generated nodes when they already exist.
             merge never edits existing nodes; it only adds missing ones.
    - reconcile: like merge, but also *repairs* the canonical chain when nodes already exist.
                 reconcile may update existing deliverable/task nodes that match the template
                 (title-based matching) to ensure required deps/fields are present.

    reconcile never removes user-provided fields or dependencies; it only adds missing
    required fields/deps and normalizes ordering deterministically.

    Scope safety:
      In reconcile mode, when reconcile_strict=True, tasks are only eligible for reconciliation
      if they already depend on the chosen deliverable. This prevents accidentally "claiming"
      a task with the same title that belongs to a different deliverable.

      When reconcile_strict=False, reconcile may fall back to title-only matching.
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

    # In reconcile mode, we may update matching existing nodes.
    node_by_id: dict[str, dict[str, Any]] = {}
    if mode == "reconcile":
        for raw in nodes:
            if isinstance(raw, dict) and isinstance(raw.get("id"), str):
                node_by_id[raw["id"]] = dict(raw)  # shallow copy

    new_nodes: list[dict[str, Any]] = []

    if mode == "merge":
        deliverables_by_key, tasks_by_key = _index_existing_for_merge(nodes)
    else:
        deliverables_by_key, tasks_by_key = ({}, {})

    # Indexes for reconcile
    deliverable_ids_by_title: dict[str, list[str]] = {}
    tasks_by_title: dict[str, list[str]] = {}
    tasks_by_title_and_del: dict[tuple[str, str], list[str]] = {}
    if mode == "reconcile":
        deliverable_ids_by_title, tasks_by_title, tasks_by_title_and_del = _index_existing_for_reconcile(nodes)

    for out_id in outcome_root_ids:
        deliverable_title = f"Deliver: {out_id}"

        # Deliverable
        if mode == "merge":
            del_candidates = deliverables_by_key.get((deliverable_title, out_id), [])
            if del_candidates:
                del_id = sorted(del_candidates)[0]
            else:
                del_id = _create_deliverable(out_id, deliverable_title, existing_ids, new_nodes)
                deliverables_by_key.setdefault((deliverable_title, out_id), []).append(del_id)
        elif mode == "reconcile":
            del_candidates = deliverable_ids_by_title.get(deliverable_title, [])
            if del_candidates:
                del_id = sorted(del_candidates)[0]
                _reconcile_deliverable(node_by_id[del_id], out_id)
            else:
                del_id = _create_deliverable(out_id, deliverable_title, existing_ids, new_nodes)
                deliverable_ids_by_title.setdefault(deliverable_title, []).append(del_id)
        else:  # append
            del_id = _create_deliverable(out_id, deliverable_title, existing_ids, new_nodes)

        # Tasks
        prev_task_id: str | None = None
        for i, title in enumerate(task_titles, start=1):
            task_title = f"{title}: {out_id}"

            if mode == "merge":
                t_candidates = tasks_by_key.get((task_title, del_id), [])
                if t_candidates:
                    t_id = sorted(t_candidates)[0]
                    prev_task_id = t_id
                    continue

            if mode == "reconcile":
                if reconcile_strict:
                    t_candidates = tasks_by_title_and_del.get((task_title, del_id), [])
                else:
                    t_candidates = tasks_by_title_and_del.get((task_title, del_id), [])
                    if not t_candidates:
                        t_candidates = tasks_by_title.get(task_title, [])

                if t_candidates:
                    t_id = sorted(t_candidates)[0]
                    _reconcile_task(node_by_id[t_id], deliverable_id=del_id, prev_task_id=prev_task_id, title=title)
                    # If we reconciled by title-only (non-strict), it now depends on del_id; register it.
                    tasks_by_title.setdefault(task_title, []).append(t_id)
                    tasks_by_title_and_del.setdefault((task_title, del_id), []).append(t_id)
                    prev_task_id = t_id
                    continue

            # Need to create a task
            t_base = f"TSK-{out_id}-{i:02d}"
            t_id = _unique_id(t_base, existing_ids)
            existing_ids.add(t_id)

            deps = _normalize_depends([], required=[del_id] + ([prev_task_id] if prev_task_id else []))

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

            if mode == "merge":
                tasks_by_key.setdefault((task_title, del_id), []).append(t_id)
            if mode == "reconcile":
                tasks_by_title.setdefault(task_title, []).append(t_id)
                tasks_by_title_and_del.setdefault((task_title, del_id), []).append(t_id)
            prev_task_id = t_id

    # Output nodes: preserve original ordering, using reconciled copies when applicable.
    if mode == "reconcile":
        out_nodes: list[Any] = []
        for raw in nodes:
            if isinstance(raw, dict) and isinstance(raw.get("id"), str) and raw["id"] in node_by_id:
                out_nodes.append(node_by_id[raw["id"]])
            else:
                out_nodes.append(raw)
        out["nodes"] = out_nodes + new_nodes
    else:
        out["nodes"] = list(nodes) + new_nodes

    return out


def dump_plan_yaml(plan: dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(plan, f, sort_keys=False, default_flow_style=False, allow_unicode=True)


def _create_deliverable(out_id: str, deliverable_title: str, existing_ids: set[str], new_nodes: list[dict[str, Any]]) -> str:
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
    return del_id


def _collect_existing_ids(nodes: list[Any]) -> set[str]:
    ids: set[str] = set()
    for raw in nodes:
        if isinstance(raw, dict):
            nid = raw.get("id")
            if isinstance(nid, str):
                ids.add(nid)
    return ids


def _index_existing_for_merge(
    nodes: list[Any],
) -> tuple[dict[tuple[str, str], list[str]], dict[tuple[str, str], list[str]]]:
    """Indexes used by merge mode."""

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


def _index_existing_for_reconcile(
    nodes: list[Any],
) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[tuple[str, str], list[str]]]:
    """Indexes used by reconcile mode.

    - deliverable_ids_by_title: deliverable title -> [deliverable_id]
    - tasks_by_title: task title -> [task_id]
    - tasks_by_title_and_del: (task title, deliverable_id) -> [task_id]
      based on tasks that already depend on deliverable_id.
    """

    deliverable_ids_by_title: dict[str, list[str]] = {}
    tasks_by_title: dict[str, list[str]] = {}
    tasks_by_title_and_del: dict[tuple[str, str], list[str]] = {}

    for raw in nodes:
        if not isinstance(raw, dict):
            continue
        nid = raw.get("id")
        ntype = raw.get("type")
        title = raw.get("title")
        depends_on = raw.get("depends_on")

        if not isinstance(nid, str) or not isinstance(ntype, str) or not isinstance(title, str):
            continue

        if ntype == "deliverable":
            if title.startswith("Deliver: "):
                deliverable_ids_by_title.setdefault(title, []).append(nid)

        elif ntype == "task":
            tasks_by_title.setdefault(title, []).append(nid)
            if isinstance(depends_on, list):
                for d in depends_on:
                    if isinstance(d, str) and d.startswith("DEL-"):
                        tasks_by_title_and_del.setdefault((title, d), []).append(nid)

    return deliverable_ids_by_title, tasks_by_title, tasks_by_title_and_del


def _reconcile_deliverable(node: dict[str, Any], out_id: str) -> None:
    # Ensure depends_on includes out_id
    depends = node.get("depends_on")
    if not isinstance(depends, list):
        depends = []
    node["depends_on"] = _normalize_depends(depends, required=[out_id])

    # Ensure DoD has at least 2 items
    dod = node.get("definition_of_done")
    if not isinstance(dod, list):
        dod = []
    dod_clean = [x for x in dod if isinstance(x, str) and x.strip()]
    if len(dod_clean) == 0:
        dod_clean = ["Implementation complete", "Reviewed and accepted"]
    elif len(dod_clean) == 1:
        dod_clean.append("Reviewed and accepted")
    node["definition_of_done"] = dod_clean


def _reconcile_task(node: dict[str, Any], *, deliverable_id: str, prev_task_id: str | None, title: str) -> None:
    # Ensure required deps
    depends = node.get("depends_on")
    if not isinstance(depends, list):
        depends = []
    required = [deliverable_id] + ([prev_task_id] if prev_task_id else [])
    node["depends_on"] = _normalize_depends(depends, required=required)

    # Ensure owner
    owner = node.get("owner")
    if not isinstance(owner, str) or not owner.strip():
        node["owner"] = "auto"

    # Ensure estimate_hours
    est = node.get("estimate_hours")
    if not isinstance(est, int) or est <= 0:
        node["estimate_hours"] = 1

    # Ensure DoD non-empty
    dod = node.get("definition_of_done")
    if not isinstance(dod, list):
        dod = []
    dod_clean = [x for x in dod if isinstance(x, str) and x.strip()]
    if not dod_clean:
        dod_clean = [f"{title} complete"]
    node["definition_of_done"] = dod_clean


def _normalize_depends(existing: list[Any], *, required: list[str]) -> list[str]:
    """Return deterministic depends_on list.

    - required deps come first, in required order
    - keep all existing string deps in their original order
    - de-dup
    """

    existing_strs = [d for d in existing if isinstance(d, str) and d.strip()]
    out: list[str] = []
    seen: set[str] = set()

    for r in required:
        if r and r not in seen:
            out.append(r)
            seen.add(r)

    for d in existing_strs:
        if d not in seen:
            out.append(d)
            seen.add(d)

    return out


def _unique_id(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        candidate = f"{base}-{ch}"
        if candidate not in existing:
            return candidate
    raise ValueError(f"could not allocate unique id for base={base}")
