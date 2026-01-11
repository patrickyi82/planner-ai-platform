from pathlib import Path

import yaml
from typer.testing import CliRunner

from planner_ai_platform.cli import app
from planner_ai_platform.core.lint.lint_plan import lint_plan
from planner_ai_platform.core.validate.validate_plan import validate_plan


runner = CliRunner()


def _load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _task_titles(plan: dict) -> list[str]:
    titles = []
    for n in plan.get("nodes", []):
        if isinstance(n, dict) and n.get("type") == "task":
            titles.append(n.get("title"))
    return [t for t in titles if isinstance(t, str)]


def test_expand_with_template_file_custom(tmp_path: Path):
    out_path = tmp_path / "expanded-custom.yaml"
    r = runner.invoke(
        app,
        [
            "expand",
            "examples/expand-input.yaml",
            "--out",
            str(out_path),
            "--template-file",
            "examples/templates.yaml",
            "--template",
            "custom",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr

    got = _load_yaml(out_path)
    titles = _task_titles(got)

    assert len(titles) == 4
    assert titles[0].startswith("Align:")
    assert titles[1].startswith("Build:")
    assert titles[2].startswith("Verify:")
    assert titles[3].startswith("Ship:")

    g, v = validate_plan(got)
    assert g is not None
    assert v == []
    assert lint_plan(got) == []
