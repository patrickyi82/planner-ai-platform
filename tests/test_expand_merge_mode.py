from pathlib import Path

import yaml
from typer.testing import CliRunner

from planner_ai_platform.cli import app
from planner_ai_platform.core.lint.lint_plan import lint_plan
from planner_ai_platform.core.validate.validate_plan import validate_plan

runner = CliRunner()


def _load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _assert_valid(plan: dict) -> None:
    g, v = validate_plan(plan)
    assert g is not None
    assert v == []
    assert lint_plan(plan) == []


def test_expand_merge_is_idempotent(tmp_path: Path):
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"

    r1 = runner.invoke(app, ["expand", "examples/expand-input.yaml", "--out", str(a)])
    assert r1.exit_code == 0, r1.stdout + r1.stderr

    r2 = runner.invoke(app, ["expand", str(a), "--out", str(b), "--mode", "merge"])
    assert r2.exit_code == 0, r2.stdout + r2.stderr

    got_a = _load_yaml(a)
    got_b = _load_yaml(b)

    assert got_a == got_b
    _assert_valid(got_b)


def test_expand_merge_is_idempotent_with_collisions(tmp_path: Path):
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"

    r1 = runner.invoke(app, ["expand", "examples/expand-collision-input.yaml", "--out", str(a)])
    assert r1.exit_code == 0, r1.stdout + r1.stderr

    r2 = runner.invoke(app, ["expand", str(a), "--out", str(b), "--mode", "merge"])
    assert r2.exit_code == 0, r2.stdout + r2.stderr

    got_a = _load_yaml(a)
    got_b = _load_yaml(b)
    assert got_a == got_b
    _assert_valid(got_b)
