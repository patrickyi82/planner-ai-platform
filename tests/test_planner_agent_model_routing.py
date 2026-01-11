from planner_agent.core.llm import model_for_role


def test_model_for_role_uses_override(monkeypatch):
    default_model = "gpt-5-mini"
    monkeypatch.setenv("OPENAI_MODEL_CODER", "gpt-5.1-codex")
    assert model_for_role("coder", default_model) == "gpt-5.1-codex"


def test_model_for_role_falls_back(monkeypatch):
    default_model = "gpt-5-mini"
    monkeypatch.delenv("OPENAI_MODEL_TESTER", raising=False)
    assert model_for_role("tester", default_model) == default_model


def test_model_for_role_sanitizes(monkeypatch):
    default_model = "gpt-5-mini"
    monkeypatch.setenv("OPENAI_MODEL_RUNTIME_EXPAND", "gpt-5.2")
    assert model_for_role("runtime-expand", default_model) == "gpt-5.2"
