from pathlib import Path

import yaml
from typer.testing import CliRunner

from planner_ai_platform.cli import app
from planner_ai_platform.core.lint.lint_plan import lint_plan
from planner_ai_platform.core.validate.validate_plan import validate_plan

runner = CliRunner()


def _load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def test_expand_id_collisions(tmp_path: Path):
    out_path = tmp_path / "expanded.yaml"
    r = runner.invoke(app, ["expand", "examples/expand-collision-input.yaml", "--out", str(out_path)])
    assert r.exit_code == 0, r.stdout + r.stderr

    got = _load_yaml(out_path)
    expected = _load_yaml(Path("examples/expand-collision-expected.yaml"))
    assert got == expected

    g, v = validate_plan(got)
    assert g is not None
    assert v == []
    assert lint_plan(got) == []


def test_expand_unknown_root_errors(tmp_path: Path):
    out_path = tmp_path / "expanded.yaml"
    r = runner.invoke(app, ["expand", "examples/expand-input.yaml", "--out", str(out_path), "--root", "NOPE-123"])
    assert r.exit_code != 0
    assert "E_EXPAND_UNKNOWN_ROOT" in (r.stdout + r.stderr)
