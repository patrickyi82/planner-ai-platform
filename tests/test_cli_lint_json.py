import json
from typer.testing import CliRunner

from planner_ai_platform.cli import app

runner = CliRunner()


def test_cli_lint_json_success():
    r = runner.invoke(app, ["lint", "examples/basic-plan.yaml", "--format", "json"])
    assert r.exit_code == 0
    payload = json.loads(r.stdout)
    assert payload["command"] == "lint"
    assert payload["sdf_version"] == "v0"
    assert payload["ok"] is True
    assert payload["error_count"] == 0
    assert payload["errors"] == []


def test_cli_lint_json_failure_contains_codes():
    r = runner.invoke(app, ["lint", "examples/invalid-duplicate-id.yaml", "--format", "json"])
    assert r.exit_code == 2
    payload = json.loads(r.stdout)
    assert payload["ok"] is False
    assert payload["sdf_version"] == "v0"
    codes = {e["code"] for e in payload["errors"]}
    assert "L_DUPLICATE_ID" in codes
