# planner-ai-platform

A platform to load/validate/lint/expand project plans (YAML/JSON), with AI-assisted expansion later.

## Quickstart (dev)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

planner --help
planner validate examples/basic-plan.yaml
pytest
```

## Status

- Phase 1 (in progress): schema v0 + loader + validator + `planner validate`

See `docs/ROADMAP.md`.
