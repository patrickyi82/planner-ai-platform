from pathlib import Path

import yaml
from typer.testing import CliRunner

from planner_ai_platform.cli import app


runner = CliRunner()


def _load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _task_titles(plan: dict) -> list[str]:
    titles = []
    for n in plan.get("nodes", []):
        if isinstance(n, dict) and n.get("type") == "task":
            titles.append(n.get("title"))
    return [t for t in titles if isinstance(t, str)]


def test_expand_template_dev(tmp_path: Path):
    out_path = tmp_path / "expanded-dev.yaml"
    r = runner.invoke(
        app, ["expand", "examples/expand-input.yaml", "--out", str(out_path), "--template", "dev"]
    )
    assert r.exit_code == 0, r.stdout + r.stderr

    got = _load_yaml(out_path)
    titles = _task_titles(got)

    # dev template has 6 tasks
    assert len(titles) == 6
    assert any(t.startswith("Review:") for t in titles)
    assert any(t.startswith("Release:") for t in titles)


def test_expand_template_ops(tmp_path: Path):
    out_path = tmp_path / "expanded-ops.yaml"
    r = runner.invoke(
        app, ["expand", "examples/expand-input.yaml", "--out", str(out_path), "--template", "ops"]
    )
    assert r.exit_code == 0, r.stdout + r.stderr

    got = _load_yaml(out_path)
    titles = _task_titles(got)

    # ops template has 5 tasks
    assert len(titles) == 5
    assert any(t.startswith("Monitoring:") for t in titles)


def test_expand_unknown_template_errors(tmp_path: Path):
    out_path = tmp_path / "expanded-unknown.yaml"
    r = runner.invoke(
        app, ["expand", "examples/expand-input.yaml", "--out", str(out_path), "--template", "nope"]
    )
    assert r.exit_code != 0
    assert "E_EXPAND_UNKNOWN_TEMPLATE" in (r.stdout + r.stderr)
