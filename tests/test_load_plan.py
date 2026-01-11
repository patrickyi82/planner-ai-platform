from planner_ai_platform.core.io.load_plan import load_plan
from planner_ai_platform.core.errors import PlanLoadError


def test_load_yaml_success():
    plan = load_plan("examples/basic-plan.yaml")
    assert plan["schema_version"] == "0.1.0"
    assert isinstance(plan["nodes"], list)


def test_load_missing_file():
    try:
        load_plan("examples/does-not-exist.yaml")
        assert False, "expected PlanLoadError"
    except PlanLoadError as e:
        assert e.code == "E_FILE_NOT_FOUND"


def test_load_unsupported_format(tmp_path):
    p = tmp_path / "plan.txt"
    p.write_text("hello", encoding="utf-8")
    try:
        load_plan(str(p))
        assert False, "expected PlanLoadError"
    except PlanLoadError as e:
        assert e.code == "E_UNSUPPORTED_FORMAT"
