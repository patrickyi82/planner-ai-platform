# Planner Plan Schema v0 (Minimal Strict)

This document defines the **current plan contract** enforced by `planner validate` (Phase 1),
with additional quality rules enforced by `planner lint` (Phase 2).

The schema is intentionally **minimal strict**:
- strict about required fields + core types
- permissive about unknown **node-level** fields (they are allowed)
- **top-level unknown keys are dropped by the loader** (see “Loader behavior”)

---

## Supported file formats

A plan may be provided as:

- YAML: `.yaml` / `.yml`
- JSON: `.json`

---

## Loader behavior (important)

`planner` loads plans via `planner_ai_platform/core/io/load_plan.py`.

### Top-level normalization
The loader **keeps only** the following top-level keys:

- `schema_version`
- `nodes`
- `root_ids` (optional; only included if present)

All other top-level keys are **ignored/dropped** at load time.

### File metadata
The loader injects an internal key:

- `__file__`: absolute/relative path to the loaded file (used for error reporting)

This key is not part of the public schema and should not be authored manually.

### Node-level behavior
Node objects are passed through as-is. Unknown keys on node objects are not removed by the loader.

---

## Top-level schema

A plan document is a mapping/object with:

### `schema_version` (required)
- Type: string
- Constraint: non-empty after `.strip()`

> Note: the validator does **not** enforce semver. Any non-empty string is accepted.

### `nodes` (required)
- Type: array/list
- Each element must be an object (mapping)

### `root_ids` (optional)
- Type: array/list of strings
- Semantics: explicitly declares roots (see Root semantics)

---

## Node schema

Each element of `nodes` must be an object with the following required fields:

### Required fields
- `id`: string (non-empty after `.strip()`)
- `type`: string, one of:
  - `outcome`
  - `deliverable`
  - `milestone`
  - `task`
  - `check`
- `title`: string (non-empty after `.strip()`)
- `definition_of_done`: array of strings
- `depends_on`: array of strings (may be empty `[]`)

### Optional fields
The validator permits these optional fields:

- `owner`: string (if present)
- `estimate_hours`: number (int or float) (if present)
- `priority`: integer (if present)

> Unknown node-level fields are allowed (not validated, not rejected).

---

## Dependency semantics

### `depends_on`
- `depends_on` is an array of node IDs.
- Each dependency must reference an existing node `id`.

Validation enforces:
- every dependency ID must exist in the plan (`E_UNKNOWN_DEPENDENCY`)

### Cycles
- Phase 1 validation does **not** reject cycles.
- Phase 2 lint detects cycles (`L_CYCLE_DETECTED`).

---

## Root semantics

Roots are used for summaries and for Phase 2 reachability lint.

### Case A: `root_ids` is not provided
Roots are inferred as:
- every node where `depends_on == []`

If no inferred roots exist, validation fails with:
- `E_NO_ROOTS`

### Case B: `root_ids` is provided
Validation rules:
- `root_ids` must be an array of strings (`E_INVALID_TYPE` if not)
- each entry must reference an existing node (`E_UNKNOWN_ROOT`)
- each root must have `depends_on: []` (`E_ROOT_HAS_DEPENDENCIES`)

If `root_ids` contains no valid roots (and `root_ids` itself had a valid type),
validation fails with:
- `E_NO_ROOTS`

> Note: roots are sorted in the output summary.

---

## Phase 2 (lint) requirements layered on top of schema

`planner lint` applies additional “SDF v0” rules:

- Tasks and checks must have **non-empty** `definition_of_done`
- Tasks must have a **non-empty** `owner`
- Nodes must be reachable from roots (based on `root_ids` or inferred roots)
- Cycles are reported

See `docs/errors.md` for lint codes.

---

## CLI behavior (validate/lint)

### `planner validate <file>`
- Exit code `0`: valid
- Exit code `1`: load error (file missing, parse error, etc.)
- Exit code `2`: validation errors

### `planner lint <file>`
- Exit code `0`: no lint or validation errors
- Exit code `1`: load error
- Exit code `2`: lint and/or validation errors

---

## Examples

### Minimal valid plan (YAML)
```yaml
schema_version: "0.1.0"
nodes:
  - id: OUT-001
    type: outcome
    title: "A thing is done"
    definition_of_done:
      - "Acceptance criteria met"
    depends_on: []
````

### Explicit roots

```yaml
schema_version: "0.1.0"
root_ids: ["OUT-001"]
nodes:
  - id: OUT-001
    type: outcome
    title: "Rooted outcome"
    definition_of_done: ["Done"]
    depends_on: []
```

### Notes on recommended fields

Even though the schema allows `definition_of_done: []`, Phase 2 lint will reject empty DoD for:

* `task`
* `check`

Similarly, schema does not require `owner`, but lint requires it for:

* `task`
