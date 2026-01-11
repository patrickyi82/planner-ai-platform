from typer.testing import CliRunner

from planner_ai_platform.cli import app


runner = CliRunner()


def test_templates_command_accepts_template_file():
    r = runner.invoke(app, ["templates", "--template-file", "examples/templates.yaml"])
    assert r.exit_code == 0, r.stdout + r.stderr
    out = r.stdout + r.stderr

    assert "Templates:" in out
    assert "- custom:" in out
