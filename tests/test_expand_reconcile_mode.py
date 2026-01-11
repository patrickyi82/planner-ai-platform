from pathlib import Path

import yaml
from typer.testing import CliRunner

from planner_ai_platform.cli import app
from planner_ai_platform.core.lint.lint_plan import lint_plan
from planner_ai_platform.core.validate.validate_plan import validate_plan


runner = CliRunner()


def _load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _node_by_title(plan: dict, title: str) -> dict:
    for n in plan.get("nodes", []):
        if isinstance(n, dict) and n.get("title") == title:
            return n
    raise AssertionError(f"missing node title={title}")


def test_expand_reconcile_repairs_and_is_idempotent(tmp_path: Path):
    out1 = tmp_path / "r1.yaml"
    out2 = tmp_path / "r2.yaml"

    r = runner.invoke(
        app,
        [
            "expand",
            "examples/expand-reconcile-input.yaml",
            "--out",
            str(out1),
            "--mode",
            "reconcile",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr

    got1 = _load_yaml(out1)

    # Validate + lint must pass after reconcile
    g, v = validate_plan(got1)
    assert g is not None
    assert v == []
    assert lint_plan(got1) == []

    # Check repaired deliverable
    d = _node_by_title(got1, "Deliver: OUT-EXP-001")
    assert "OUT-EXP-001" in d["depends_on"]
    assert isinstance(d["definition_of_done"], list)
    assert len(d["definition_of_done"]) >= 2

    # Check repaired task chain deps ordering
    t1 = _node_by_title(got1, "Design: OUT-EXP-001")
    t2 = _node_by_title(got1, "Implement: OUT-EXP-001")
    t3 = _node_by_title(got1, "Test: OUT-EXP-001")
    t4 = _node_by_title(got1, "Docs: OUT-EXP-001")

    did = d["id"]
    assert t1["depends_on"][0] == did
    assert t2["depends_on"][0] == did and t2["depends_on"][1] == t1["id"]
    assert t3["depends_on"][0] == did and t3["depends_on"][1] == t2["id"]
    assert t4["depends_on"][0] == did and t4["depends_on"][1] == t3["id"]

    # Required fields repaired
    for t in (t1, t2, t3, t4):
        assert isinstance(t.get("owner"), str) and t["owner"].strip()
        assert isinstance(t.get("estimate_hours"), int) and t["estimate_hours"] > 0
        assert isinstance(t.get("definition_of_done"), list) and len(t["definition_of_done"]) > 0

    # Idempotent: running reconcile again produces identical output
    r = runner.invoke(app, ["expand", str(out1), "--out", str(out2), "--mode", "reconcile"])
    assert r.exit_code == 0, r.stdout + r.stderr
    got2 = _load_yaml(out2)
    assert got1 == got2
