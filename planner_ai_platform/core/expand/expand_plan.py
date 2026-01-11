from __future__ import annotations

from typing import Any

import yaml


TEMPLATE_TASK_TITLES: dict[str, list[str]] = {
    # Phase 3 baseline: keep this stable for golden tests.
    "simple": ["Design", "Implement", "Test", "Docs"],
    # Slightly richer dev lifecycle.
    "dev": ["Design", "Implement", "Test", "Docs", "Review", "Release"],
    # Ops-focused expansion.
    # (Avoid using terms that can be interpreted as emergency/dispatch language.)
    "ops": ["Monitoring", "SLOs", "Runbooks", "Playbooks", "Reliability"],
}


def expand_plan_dict(
    plan: dict[str, Any],
    *,
    outcome_root_ids: list[str],
    template: str = "simple",
) -> dict[str, Any]:
    """Return a new expanded plan dict (deterministic, no AI).

    Notes:
    - This function is intentionally pure/deterministic for Phase 3.
    - Callers should validate `template` against TEMPLATE_TASK_TITLES.
    """

    schema_version = plan.get("schema_version")
    nodes = plan.get("nodes")

    # Keep output minimal: schema_version, nodes, optional root_ids
    out: dict[str, Any] = {
        "schema_version": schema_version,
        "nodes": [],
    }
    if "root_ids" in plan:
        out["root_ids"] = plan.get("root_ids")

    if not isinstance(nodes, list):
        # Validator should have caught this; keep best-effort.
        out["nodes"] = nodes
        return out

    task_titles = TEMPLATE_TASK_TITLES.get(template, TEMPLATE_TASK_TITLES["simple"])

    existing_ids = _collect_existing_ids(nodes)
    new_nodes: list[dict[str, Any]] = []

    for out_id in outcome_root_ids:
        # Deliverable
        del_base = f"DEL-{out_id}-01"
        del_id = _unique_id(del_base, existing_ids)
        existing_ids.add(del_id)

        new_nodes.append(
            {
                "id": del_id,
                "type": "deliverable",
                "title": f"Deliver: {out_id}",
                "definition_of_done": [
                    "Implementation complete",
                    "Reviewed and accepted",
                ],
                "depends_on": [out_id],
            }
        )

        # Tasks under deliverable
        prev_task_id: str | None = None
        for i, title in enumerate(task_titles, start=1):
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
                    "title": f"{title}: {out_id}",
                    "definition_of_done": [f"{title} complete"],
                    "depends_on": deps,
                    "owner": "auto",
                    "estimate_hours": 1,
                }
            )
            prev_task_id = t_id

    # Preserve existing node ordering; append new nodes deterministically.
    out["nodes"] = list(nodes) + new_nodes
    return out


def dump_plan_yaml(plan: dict[str, Any], path: str) -> None:
    """Write a plan dict to YAML (stable, readable)."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            plan,
            f,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
        )


def _collect_existing_ids(nodes: list[Any]) -> set[str]:
    ids: set[str] = set()
    for raw in nodes:
        if isinstance(raw, dict):
            nid = raw.get("id")
            if isinstance(nid, str):
                ids.add(nid)
    return ids


def _unique_id(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        candidate = f"{base}-{ch}"
        if candidate not in existing:
            return candidate
    raise ValueError(f"could not allocate unique id for base={base}")
