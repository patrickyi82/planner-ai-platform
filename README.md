# planner-ai-platform

A platform to load/validate/lint/expand project plans (YAML/JSON), with AI-assisted expansion later.

## Quickstart (dev)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

planner --help
planner validate examples/basic-plan.yaml
planner lint examples/basic-plan.yaml
planner expand examples/expand-input.yaml --out /tmp/expanded.yaml --template simple
planner expand examples/expand-input.yaml --out /tmp/expanded-dev.yaml --template dev
pytest
```

## Agent runner (local)

```bash
# Adds OpenAI + rich
pip install -e .[dev,agents]

planner-agent repomap
planner-agent run "Add a new lint command"
```

See `docs/AGENTS.md`.

## Status

- Phase 1 (in progress): schema v0 + loader + validator + `planner validate`

See `docs/ROADMAP.md`.
