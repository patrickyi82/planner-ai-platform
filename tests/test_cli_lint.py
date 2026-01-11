from typer.testing import CliRunner

from planner_ai_platform.cli import app


runner = CliRunner()


def test_cli_lint_success():
    r = runner.invoke(app, ["lint", "examples/basic-plan.yaml"])
    assert r.exit_code == 0
    assert "OK:" in r.stdout


def test_cli_lint_duplicate_id():
    r = runner.invoke(app, ["lint", "examples/invalid-duplicate-id.yaml"])
    assert r.exit_code != 0
    out = r.stdout + r.stderr
    assert "L_DUPLICATE_ID" in out
