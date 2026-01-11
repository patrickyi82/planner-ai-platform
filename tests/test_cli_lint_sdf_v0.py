from typer.testing import CliRunner

from planner_ai_platform.cli import app


runner = CliRunner()


def test_lint_empty_dod_task():
    r = runner.invoke(app, ["lint", "examples/invalid-empty-dod.yaml"])
    assert r.exit_code != 0
    out = r.stdout + r.stderr
    assert "L_EMPTY_DEFINITION_OF_DONE" in out


def test_lint_missing_owner_task():
    r = runner.invoke(app, ["lint", "examples/invalid-missing-owner.yaml"])
    assert r.exit_code != 0
    out = r.stdout + r.stderr
    assert "L_TASK_MISSING_OWNER" in out


def test_lint_cycle_detected():
    r = runner.invoke(app, ["lint", "examples/invalid-cycle.yaml"])
    assert r.exit_code != 0
    out = r.stdout + r.stderr
    assert "L_CYCLE_DETECTED" in out


def test_lint_unreachable_node():
    r = runner.invoke(app, ["lint", "examples/invalid-unreachable.yaml"])
    assert r.exit_code != 0
    out = r.stdout + r.stderr
    assert "L_UNREACHABLE_NODE" in out
