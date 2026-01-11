from typer.testing import CliRunner

from planner_ai_platform.cli import app


runner = CliRunner()


def test_cli_validate_success():
    r = runner.invoke(app, ["validate", "examples/basic-plan.yaml"])
    assert r.exit_code == 0
    assert "OK:" in r.stdout
    assert "Roots:" in r.stdout


def test_cli_validate_failure():
    r = runner.invoke(app, ["validate", "examples/invalid-unknown-dep.yaml"])
    assert r.exit_code != 0
    assert "E_UNKNOWN_DEPENDENCY" in (r.stdout + r.stderr)
