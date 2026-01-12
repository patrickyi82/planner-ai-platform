# ADR-0002: Phase 4 AI-assisted expansion via patch contract

## Status
Accepted

## Context
Phase 1–3 provide deterministic workflows:
- `planner validate`
- `planner lint`
- `planner expand` (deterministic, templates, idempotent modes)

Phase 4 must add AI-assisted expansion without destabilizing Phase 1–3.

## Decision
Add a new command: `planner ai-expand` (do NOT modify deterministic `planner expand` behavior).

The LLM must return a structured JSON patch plan:
- add_nodes: list of complete node objects
- update_nodes: list of id + partial `set` fields
- notes: list of strings

The planner applies patches deterministically:
- resolves ID conflicts via deterministic reallocation
- applies updates additively (does not delete existing fields)

A bounded repair loop enforces quality gates:
- after each patch application, run `validate` + `lint`
- stop when gates pass, or after `max_fix_rounds`
- allow parallel suggestion generation via worker pool

## Consequences
- Deterministic workflows remain stable.
- AI output is constrained and auditable.
- Unit tests do not require live OpenAI calls (FakeLLM).
