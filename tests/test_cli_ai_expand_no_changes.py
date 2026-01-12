from typer.testing import CliRunner

from planner_ai_platform.cli import app


runner = CliRunner()


def test_cli_ai_expand_fails_if_no_changes(monkeypatch, tmp_path):
    # Provide dummy key so command does not exit early on key check.
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    # Monkeypatch OpenAIPatchClient to return an empty edit plan.
    from planner_ai_platform.core.ai.contracts import EditPlan

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def propose_patch(self, *, context, model):
            return EditPlan(add_nodes=[], update_nodes=[], notes=["noop"])

    import planner_ai_platform.cli as cli_mod

    monkeypatch.setattr(cli_mod, "OpenAIPatchClient", FakeClient)

    out = tmp_path / "ai.yaml"
    r = runner.invoke(
        app,
        [
            "ai-expand",
            "examples/basic-plan.yaml",
            "--out",
            str(out),
            "--max-fix-rounds",
            "1",
            "--workers",
            "1",
        ],
    )
    assert r.exit_code == 2
    assert "E_AI_EXPAND_NO_CHANGES" in (r.stdout + r.stderr)
