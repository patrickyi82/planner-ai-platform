# planner-ai-platform

A platform to load/validate/lint/expand project plans (YAML/JSON), with AI-assisted expansion later.

## Quickstart (dev)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

planner --help

# Phase 1/2: validate + lint
planner validate examples/basic-plan.yaml
planner lint examples/basic-plan.yaml

# Phase 3: templates + expansion
planner templates
planner templates --template-file examples/templates.yaml

planner expand examples/expand-input.yaml --out /tmp/expanded.yaml --template simple
planner validate /tmp/expanded.yaml
planner lint /tmp/expanded.yaml

# idempotent expansion
planner expand /tmp/expanded.yaml --out /tmp/expanded2.yaml --mode merge
diff -u /tmp/expanded.yaml /tmp/expanded2.yaml || true

# repair + scope-safe reconcile
planner expand examples/expand-reconcile-input.yaml --out /tmp/reconciled.yaml --mode reconcile
planner lint /tmp/reconciled.yaml

planner expand examples/expand-reconcile-scope-safe.yaml --out /tmp/scope-safe.yaml --mode reconcile --reconcile-strict
planner lint /tmp/scope-safe.yaml

pytest
```

## Expansion (Phase 3)

### Templates

Built-in deterministic templates:

- `simple`: Design, Implement, Test, Docs
- `dev`: Design, Implement, Test, Docs, Review, Release
- `ops`: Monitoring, SLOs, Runbooks, Playbooks, Reliability

List templates:

```bash
planner templates
planner templates --template-file examples/templates.yaml
```

Use a template:

```bash
planner expand examples/expand-input.yaml --out /tmp/expanded.yaml --template dev
planner expand examples/expand-input.yaml --out /tmp/expanded.yaml --template-file examples/templates.yaml --template custom
```

### Expansion modes

- `--mode append` (default): always creates a new deliverable + task chain.
- `--mode merge`: idempotent; reuses previously generated nodes when possible; never edits existing nodes.
- `--mode reconcile`: idempotent + repairs the canonical chain when matching nodes already exist (adds missing required deps/fields).

Reconcile scoping:

- `--reconcile-strict` (default): only reuses tasks that already depend on the chosen deliverable (prevents accidentally “claiming” same-title tasks from another deliverable).
- `--reconcile-loose`: allows fallback to title-only matching.

### Examples

- `examples/expand-input.yaml`: happy-path expansion input.
- `examples/templates.yaml`: example external template config.
- `examples/expand-reconcile-input.yaml`: intentionally “broken” input to demonstrate `--mode reconcile` repairs.
- `examples/expand-reconcile-scope-safe.yaml`: demonstrates strict vs loose reconciliation scoping.

## Agent runner (local)

```bash
# Adds OpenAI + rich
pip install -e .[dev,agents]

planner-agent repomap
planner-agent run "Add a new lint command"
```

See `docs/AGENTS.md`.

> Note: the agent runner is experimental. Core quality gates for this repo are the deterministic CLI commands + pytest.

## Status

- ✅ Phase 1: schema v0 + loader + validator + `planner validate`
- ✅ Phase 2: SDF v0 linter + `planner lint`
- ✅ Phase 3: deterministic expansion engine + templates (+ external template file) + merge/reconcile modes
- ⏭️ Phase 4: AI-assisted expansion (planned)

See `docs/ROADMAP.md`.
