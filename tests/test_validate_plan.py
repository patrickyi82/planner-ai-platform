from planner_ai_platform.core.io.load_plan import load_plan
from planner_ai_platform.core.validate.validate_plan import validate_plan


def test_validate_happy_path():
    plan = load_plan("examples/basic-plan.yaml")
    graph, errors = validate_plan(plan)
    assert errors == []
    assert graph is not None
    assert "OUT-001" in graph.nodes_by_id
    assert len(graph.roots) >= 1


def test_validate_missing_required_field():
    plan = load_plan("examples/invalid-missing-field.yaml")
    graph, errors = validate_plan(plan)
    assert graph is None
    codes = [e.code for e in errors]
    assert "E_INVALID_TYPE" in codes or "E_REQUIRED_FIELD" in codes


def test_validate_bad_type_shape():
    plan = load_plan("examples/invalid-bad-type.yaml")
    graph, errors = validate_plan(plan)
    assert graph is None
    assert any(e.code == "E_INVALID_TYPE" for e in errors)


def test_validate_unknown_dependency():
    plan = load_plan("examples/invalid-unknown-dep.yaml")
    graph, errors = validate_plan(plan)
    assert graph is None
    assert any(e.code == "E_UNKNOWN_DEPENDENCY" for e in errors)
