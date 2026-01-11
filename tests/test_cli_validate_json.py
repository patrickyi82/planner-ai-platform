import json
from typer.testing import CliRunner

from planner_ai_platform.cli import app

runner = CliRunner()


def test_cli_validate_json_success():
    r = runner.invoke(app, ["validate", "examples/basic-plan.yaml", "--format", "json"])
    assert r.exit_code == 0
    payload = json.loads(r.stdout)
    assert payload["command"] == "validate"
    assert payload["ok"] is True
    assert payload["error_count"] == 0
    assert payload["errors"] == []
    assert payload["summary"]["node_count"] > 0
    assert "roots" in payload["summary"]


def test_cli_validate_json_failure_contains_codes():
    r = runner.invoke(app, ["validate", "examples/invalid-unknown-dep.yaml", "--format", "json"])
    assert r.exit_code == 2
    payload = json.loads(r.stdout)
    assert payload["ok"] is False
    codes = {e["code"] for e in payload["errors"]}
    assert "E_UNKNOWN_DEPENDENCY" in codes
