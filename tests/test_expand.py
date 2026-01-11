from pathlib import Path

import yaml
from typer.testing import CliRunner

from planner_ai_platform.cli import app
from planner_ai_platform.core.lint.lint_plan import lint_plan
from planner_ai_platform.core.validate.validate_plan import validate_plan

runner = CliRunner()


def _load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def test_expand_matches_expected(tmp_path: Path):
    out_path = tmp_path / "expanded.yaml"
    r = runner.invoke(app, ["expand", "examples/expand-input.yaml", "--out", str(out_path)])
    assert r.exit_code == 0, r.stdout + r.stderr

    got = _load_yaml(out_path)
    expected = _load_yaml(Path("examples/expand-expected.yaml"))
    assert got == expected

    g, v = validate_plan(got)
    assert g is not None
    assert v == []
    assert lint_plan(got) == []


def test_expand_is_deterministic(tmp_path: Path):
    out1 = tmp_path / "expanded1.yaml"
    out2 = tmp_path / "expanded2.yaml"

    r1 = runner.invoke(app, ["expand", "examples/expand-input.yaml", "--out", str(out1)])
    r2 = runner.invoke(app, ["expand", "examples/expand-input.yaml", "--out", str(out2)])

    assert r1.exit_code == 0
    assert r2.exit_code == 0

    assert out1.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")
