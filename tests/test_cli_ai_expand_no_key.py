from typer.testing import CliRunner

from planner_ai_platform.cli import app


runner = CliRunner()


def test_cli_ai_expand_requires_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    out = tmp_path / "ai.yaml"
    r = runner.invoke(app, ["ai-expand", "examples/basic-plan.yaml", "--out", str(out)])
    assert r.exit_code == 2
    assert "E_AI_EXPAND_NO_API_KEY" in (r.stdout + r.stderr)
