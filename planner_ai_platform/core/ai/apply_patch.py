from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from planner_ai_platform.core.ai.contracts import EditPlan


@dataclass(frozen=True)
class ApplyPatchResult:
    plan: dict[str, Any]
    id_remap: dict[str, str]
    notes: list[str]


def _suffixes():
    letters = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
    for a in letters:
        yield a
    for a in letters:
        for b in letters:
            yield a + b


def allocate_unique_id(existing: set[str], proposed: str) -> str:
    if proposed not in existing:
        return proposed
    for suf in _suffixes():
        candidate = f"{proposed}-{suf}"
        if candidate not in existing:
            return candidate
    raise RuntimeError(f"Unable to allocate unique id for {proposed}")


def apply_patch(plan: dict[str, Any], patch: EditPlan) -> ApplyPatchResult:
    plan2: dict[str, Any] = deepcopy(plan)
    nodes: list[dict[str, Any]] = plan2.setdefault("nodes", [])
    if not isinstance(nodes, list):
        raise ValueError("plan.nodes must be a list")

    nodes_by_id: dict[str, dict[str, Any]] = {}
    for n in nodes:
        if isinstance(n, dict) and isinstance(n.get("id"), str):
            nodes_by_id[n["id"]] = n

    existing_ids = set(nodes_by_id.keys())
    id_remap: dict[str, str] = {}

    add_nodes_materialized: list[dict[str, Any]] = []
    for add in patch.add_nodes:
        node = deepcopy(add.node)
        proposed_id = node.get("id")
        if not isinstance(proposed_id, str) or not proposed_id:
            raise ValueError("add_nodes[].node.id must be a non-empty string")
        new_id = allocate_unique_id(existing_ids, proposed_id)
        if new_id != proposed_id:
            id_remap[proposed_id] = new_id
        node["id"] = new_id
        existing_ids.add(new_id)
        add_nodes_materialized.append(node)

    def remap_id(x: Any) -> Any:
        if isinstance(x, str):
            return id_remap.get(x, x)
        if isinstance(x, list):
            return [remap_id(i) for i in x]
        return x

    for node in add_nodes_materialized:
        if "depends_on" in node:
            node["depends_on"] = remap_id(node.get("depends_on"))

    nodes.extend(add_nodes_materialized)

    for upd in patch.update_nodes:
        target_id = id_remap.get(upd.id, upd.id)
        target = nodes_by_id.get(target_id)
        if target is None:
            continue

        for k, v in upd.fields.items():
            if v is None:
                continue
            v2 = remap_id(v)

            if isinstance(v2, list) and isinstance(target.get(k), list):
                existing_list = target[k]
                for item in v2:
                    if item not in existing_list:
                        existing_list.append(item)
            elif k not in target:
                target[k] = v2
            else:
                cur = target.get(k)
                if cur is None or cur == "" or cur == []:
                    target[k] = v2

    return ApplyPatchResult(plan=plan2, id_remap=id_remap, notes=patch.notes)
