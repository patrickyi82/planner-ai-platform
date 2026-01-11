from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


Role = Literal["coder", "tester", "docs", "reviewer", "fixer"]


@dataclass(frozen=True)
class FileEdit:
    path: str
    content: str


@dataclass(frozen=True)
class Patch:
    """A patch proposal: a set of full-file writes.

    We intentionally use full-file writes rather than line diffs for v0 reliability.
    """

    edits: list[FileEdit]
    summary: str
    role: Role
    confidence: float = 0.5


@dataclass(frozen=True)
class GateResult:
    ok: bool
    name: str
    command: str
    exit_code: int
    output: str


@dataclass(frozen=True)
class RunResult:
    ok: bool
    applied_patches: list[Patch]
    gates: list[GateResult]
    notes: Optional[str] = None

    # Eval / monitoring (optional)
    model: Optional[str] = None
    models_used: dict[str, int] = field(default_factory=dict)
    llm_calls: int = 0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
