from typer.testing import CliRunner

from planner_ai_platform.cli import app


runner = CliRunner()


def test_templates_command_lists_templates():
    r = runner.invoke(app, ["templates"])
    assert r.exit_code == 0, r.stdout + r.stderr
    out = (r.stdout + r.stderr)

    assert "Templates:" in out
    # must include all template names
    assert "- simple:" in out
    assert "- dev:" in out
    assert "- ops:" in out
