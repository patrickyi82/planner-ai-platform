# planner-agent

A local, CLI-first multi-agent runner that operates directly inside this repo.

## Install

```bash
pip install -e .[dev,agents]
```

## Usage

### Repo inventory

```bash
planner-agent repomap
```

### Run a slice (autopilot)

```bash
# With OPENAI_API_KEY set, this will ask multiple agents to propose patches, apply them,
# then run gates (pytest + planner validate).
planner-agent run "Implement SDF v0 lint rules" --workers 3
```

### Use lint

```bash
planner lint examples/basic-plan.yaml
planner lint examples/invalid-cycle.yaml
```

## Safety and quality

- Agents propose patches in parallel.
- Patches are applied serially.
- Gates run after each patch:
  - `pytest`
  - `planner validate examples/basic-plan.yaml`

If a gate fails, the fixer agent attempts up to N repair rounds.

## Prompt tuning (v0)

Prompts live in code (`planner_agent/core/prompts.py`).

Next step: add prompt versions + run logs + a simple bandit to pick prompt variants.
