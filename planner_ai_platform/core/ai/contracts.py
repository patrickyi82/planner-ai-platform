from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AddNode:
    node: dict[str, Any]


@dataclass(frozen=True)
class UpdateNode:
    id: str
    fields: dict[str, Any]


@dataclass(frozen=True)
class EditPlan:
    add_nodes: list[AddNode]
    update_nodes: list[UpdateNode]
    notes: list[str]


def parse_edit_plan(obj: dict[str, Any]) -> EditPlan:
    if not isinstance(obj, dict):
        raise ValueError("EditPlan must be an object")

    add_nodes_raw = obj.get("add_nodes", [])
    update_nodes_raw = obj.get("update_nodes", [])
    notes_raw = obj.get("notes", [])

    if not isinstance(add_nodes_raw, list):
        raise ValueError("add_nodes must be a list")
    if not isinstance(update_nodes_raw, list):
        raise ValueError("update_nodes must be a list")
    if not isinstance(notes_raw, list) or any(not isinstance(x, str) for x in notes_raw):
        raise ValueError("notes must be a list[str]")

    add_nodes: list[AddNode] = []
    for item in add_nodes_raw:
        if not isinstance(item, dict) or "node" not in item or not isinstance(item["node"], dict):
            raise ValueError("Each add_nodes item must be {node: {...}}")
        add_nodes.append(AddNode(node=item["node"]))

    update_nodes: list[UpdateNode] = []
    for item in update_nodes_raw:
        if not isinstance(item, dict):
            raise ValueError("Each update_nodes item must be an object")
        node_id = item.get("id")
        fields = item.get("fields")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("update_nodes[].id must be a non-empty string")
        if not isinstance(fields, dict):
            raise ValueError("update_nodes[].fields must be an object")
        update_nodes.append(UpdateNode(id=node_id, fields=fields))

    return EditPlan(add_nodes=add_nodes, update_nodes=update_nodes, notes=notes_raw)
