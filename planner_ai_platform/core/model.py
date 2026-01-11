from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


NodeType = Literal["outcome", "deliverable", "milestone", "task", "check"]


@dataclass(frozen=True)
class PlanNode:
    id: str
    type: NodeType
    title: str
    definition_of_done: list[str]
    depends_on: list[str]

    owner: Optional[str] = None
    estimate_hours: Optional[float] = None
    priority: Optional[int] = None


@dataclass(frozen=True)
class PlanGraph:
    schema_version: str
    nodes_by_id: dict[str, PlanNode]
    edges: list[tuple[str, str]]  # (node_id, depends_on_id)
    roots: list[str]
