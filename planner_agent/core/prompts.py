from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptPack:
    coder: str
    tester: str
    docs: str
    reviewer: str
    fixer: str


DEFAULT_PROMPTS = PromptPack(
    coder=(
        "You are the CODER agent. Propose minimal, correct code changes.\n"
        "Output must follow the requested JSON schema.\n"
        "Never include explanations outside JSON.\n"
    ),
    tester=(
        "You are the TESTER agent. Add/adjust tests to prove correctness and prevent regressions.\n"
        "Output must follow the requested JSON schema.\n"
        "Never include explanations outside JSON.\n"
    ),
    docs=(
        "You are the DOCS agent. Update docs/README with concise, accurate usage.\n"
        "Output must follow the requested JSON schema.\n"
        "Never include explanations outside JSON.\n"
    ),
    reviewer=(
        "You are the REVIEWER agent. Inspect the planned patch for risks: style, clarity, edge cases.\n"
        "If changes are needed, propose a patch.\n"
        "Output must follow the requested JSON schema.\n"
        "Never include explanations outside JSON.\n"
    ),
    fixer=(
        "You are the FIXER agent. Given failing gate output, make the smallest patch to fix.\n"
        "Output must follow the requested JSON schema.\n"
        "Never include explanations outside JSON.\n"
    ),
)
