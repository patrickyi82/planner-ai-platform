# ADR-0001: Phase 1 decisions

## Status
Accepted

## Context
Phase 1 implements plan schema v0 + loader + validator + `planner validate` CLI.

We record cross-cutting decisions to prevent drift.

## Decisions

1. **Language/runtime:** Python (>= 3.11)
2. **CLI framework:** Typer
3. **Schema version format:** SemVer string (e.g., `0.1.0`). Phase 1 accepts any non-empty string.
4. **Field names (schema v0):**
   - `estimate_hours` (not `estimate`)
   - `definition_of_done` as `list[str]`
5. **Error model:**
   - structured errors with fields: `code`, `message`, `file`, `path`
   - errors printed sorted by: `file`, then `path`, then `code`

## Consequences
- Future phases should preserve these conventions unless superseded by a newer ADR.
