from pathlib import Path

import yaml
from typer.testing import CliRunner

from planner_ai_platform.cli import app


runner = CliRunner()


def _load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _nodes_by_title(plan: dict, title: str) -> list[dict]:
    out = []
    for n in plan.get("nodes", []):
        if isinstance(n, dict) and n.get("title") == title:
            out.append(n)
    return out


def test_reconcile_strict_does_not_claim_foreign_task(tmp_path: Path):
    out_path = tmp_path / "strict.yaml"

    r = runner.invoke(
        app,
        [
            "expand",
            "examples/expand-reconcile-scope-safe.yaml",
            "--out",
            str(out_path),
            "--mode",
            "reconcile",
            "--reconcile-strict",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr

    got = _load_yaml(out_path)
    designs = _nodes_by_title(got, "Design: OUT-EXP-001")

    # One is the original foreign task, plus a newly created scoped task.
    assert len(designs) == 2

    foreign = [n for n in designs if n["id"] == "TSK-FOREIGN-01"][0]
    assert foreign["depends_on"] == ["DEL-OUT-EXP-001-01-A"]

    # The newly created task should depend on the chosen lowest deliverable id.
    created = [n for n in designs if n["id"] != "TSK-FOREIGN-01"][0]
    assert created["depends_on"][0] == "DEL-OUT-EXP-001-01"


def test_reconcile_loose_can_claim_by_title(tmp_path: Path):
    out_path = tmp_path / "loose.yaml"

    r = runner.invoke(
        app,
        [
            "expand",
            "examples/expand-reconcile-scope-safe.yaml",
            "--out",
            str(out_path),
            "--mode",
            "reconcile",
            "--reconcile-loose",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr

    got = _load_yaml(out_path)
    designs = _nodes_by_title(got, "Design: OUT-EXP-001")

    # In loose mode we reconcile by title, so only the original task exists.
    assert len(designs) == 1

    # It should now have the chosen deliverable id as a required dependency (prepended).
    assert designs[0]["depends_on"][0] == "DEL-OUT-EXP-001-01"
