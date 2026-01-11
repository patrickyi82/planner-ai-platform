# Planner Errors and Codes

This document is the **code catalog** for errors emitted by:

- Phase 1: loader + `planner validate`
- Phase 2: `planner lint`
- Phase 3: deterministic expansion CLI (`planner templates`, `planner expand`)

Errors are emitted as `PlanError` (or subclasses) and printed by the CLI.

---

## Error envelope format

All errors include:

- `code`: stable identifier (e.g. `E_NO_ROOTS`, `L_CYCLE_DETECTED`)
- `message`: human-readable explanation
- `file`: optional file path
- `path`: optional logical path within plan or CLI option (e.g. `nodes[3].id`, `template_file`)

### CLI display format
The CLI prints:

- If both file and path are present:
  - `<file>:<path>: <code>: <message>`
- If only path is present:
  - `<path>: <code>: <message>`
- If neither is present:
  - `<plan>: <code>: <message>`

Examples:
- `examples/basic-plan.yaml:nodes[0].id: E_REQUIRED_FIELD: id is required and must be a non-empty string`
- `template_file: E_TEMPLATE_FILE_NOT_FOUND: template file not found: ...`

---

## Exit codes by command

### `planner validate`
- `0`: OK
- `1`: load error
- `2`: validation errors

### `planner lint`
- `0`: OK
- `1`: load error
- `2`: lint and/or validation errors

### `planner templates`
- `0`: OK
- `1`: template file not found
- `2`: template file invalid

### `planner expand`
- `0`: OK
- `1`: plan load error OR template file not found
- `2`: plan validation error OR template invalid OR expand option error OR (post-expand) validate/lint failed

---

# E_* codes (errors)

## Loader errors (PlanLoadError)

### `E_FILE_NOT_FOUND`
- When: input plan file path does not exist
- Source: `core/io/load_plan.py`
- Typical fix: correct path

### `E_FILE_READ`
- When: file exists but cannot be read
- Source: `core/io/load_plan.py`
- Typical fix: permissions / filesystem

### `E_UNSUPPORTED_FORMAT`
- When: file suffix not in `.yaml/.yml/.json`
- Source: `core/io/load_plan.py`
- Typical fix: convert to supported format

### `E_YAML_PARSE`
- When: YAML parse failed
- Source: `core/io/load_plan.py`
- Typical fix: fix YAML syntax

### `E_JSON_PARSE`
- When: JSON parse failed
- Source: `core/io/load_plan.py`
- Typical fix: fix JSON syntax

### `E_INVALID_TOP_LEVEL`
- When: top-level document is not an object/mapping
- Source: `core/io/load_plan.py`
- Typical fix: ensure `{...}` in JSON or mapping in YAML

---

## Validation errors (PlanValidationError)

### `E_REQUIRED_FIELD`
- When:
  - missing/empty `schema_version`
  - missing/non-array `nodes`
  - missing/empty node `id`
  - missing/empty node `title`
- Source: `core/validate/validate_plan.py`
- Typical fix: provide the required field with correct type

### `E_INVALID_TYPE`
- When:
  - node item is not an object
  - `definition_of_done` is not `list[str]`
  - `depends_on` is not `list[str]`
  - optional fields have wrong type:
    - `owner` not string
    - `estimate_hours` not number
    - `priority` not int
  - `root_ids` present but not `list[str]`
- Source: `core/validate/validate_plan.py`

### `E_INVALID_ENUM`
- When: `type` is not one of:
  - `outcome|deliverable|milestone|task|check`
- Source: `core/validate/validate_plan.py`

### `E_DUPLICATE_ID`
- When: duplicate node `id` detected during validation
- Source: `core/validate/validate_plan.py`
- Note: validation reports duplicates on the later occurrence(s)

### `E_UNKNOWN_DEPENDENCY`
- When: a `depends_on` entry references an unknown node id
- Source: `core/validate/validate_plan.py`

### `E_NO_ROOTS`
- When:
  - no inferred roots exist (no node with `depends_on: []`), OR
  - `root_ids` provided but yields no valid roots (after filtering invalid ones)
- Source: `core/validate/validate_plan.py`

### `E_UNKNOWN_ROOT`
- When: `root_ids[i]` references an unknown node id
- Source: `core/validate/validate_plan.py`

### `E_ROOT_HAS_DEPENDENCIES`
- When: a node listed in `root_ids` has non-empty `depends_on`
- Source: `core/validate/validate_plan.py`

---

## Template file / expand option errors

### `E_TEMPLATE_FILE_NOT_FOUND` (PlanLoadError)
- When: `--template-file` path does not exist
- Source: `planner_ai_platform/cli.py`
- Typical fix: correct path

### `E_TEMPLATE_FILE_INVALID` (PlanValidationError)
- When: template file exists but is invalid
- Source: `core/expand/template_config.py` → raised as `TemplateConfigError`, wrapped in CLI
- Template file format must be:
  - mapping of `name -> non-empty list[str]`
  - names and items must be non-empty strings

### `E_EXPAND_UNKNOWN_ROOT`
- When: `planner expand --root <id>` references unknown node id
- Source: `planner_ai_platform/cli.py`

### `E_EXPAND_UNSUPPORTED_ROOT_TYPE`
- When: `--root` references a node whose `type != outcome`
- Source: `planner_ai_platform/cli.py`

### `E_EXPAND_NO_OUTCOME_ROOTS`
- When: roots exist but none are `type: outcome` (and `--root` not provided)
- Source: `planner_ai_platform/cli.py`

### `E_EXPAND_UNKNOWN_TEMPLATE`
- When: `--template` not found in merged templates (defaults + template-file overrides)
- Source: `planner_ai_platform/cli.py`

### `E_EXPAND_UNKNOWN_MODE`
- When: `--mode` not one of `append|merge|reconcile`
- Source: `planner_ai_platform/cli.py`

---

# L_* codes (lint)

Lint codes are emitted as `PlanValidationError` with `code` starting with `L_`.

## `L_DUPLICATE_ID`
- When: duplicate node IDs are present (best-effort scan of raw nodes)
- Source: `core/lint/lint_plan.py`
- Note: lint reports duplicates on later occurrence(s) and includes `count=...`

## `L_EMPTY_DEFINITION_OF_DONE`
- When: `task` or `check` has `definition_of_done: []`
- Source: `core/lint/lint_plan.py`

## `L_TASK_MISSING_OWNER`
- When: `task.owner` is missing or empty/whitespace
- Source: `core/lint/lint_plan.py`

## `L_UNREACHABLE_NODE`
- When: node is not reachable from roots
- Root selection:
  - if `root_ids` is present and valid, lint uses the subset of those with `depends_on: []`
  - otherwise lint uses inferred roots (`depends_on: []`)
- Source: `core/lint/lint_plan.py`

## `L_CYCLE_DETECTED`
- When: dependency cycle exists (DFS with back-edge detection)
- Message includes a readable cycle path: `A -> B -> C -> A`
- Source: `core/lint/lint_plan.py`

---

## Notes / invariants

- Phase 1 validation does not enforce:
  - acyclicity
  - reachability
  - non-empty DoD for all types
  - task owner required

Those are Phase 2 lint responsibilities.

- `planner expand` always validates + lints the output plan before writing it.
  If post-expand validate/lint fails, it exits with code `2` and prints errors.
