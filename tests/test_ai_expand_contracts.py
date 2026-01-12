from planner_ai_platform.core.ai.contracts import parse_edit_plan


def test_parse_edit_plan_happy():
    obj = {
        "add_nodes": [{"node": {"id": "X", "type": "task"}}],
        "update_nodes": [{"id": "A", "fields": {"owner": "x"}}],
        "notes": ["n"],
    }
    edit = parse_edit_plan(obj)
    assert len(edit.add_nodes) == 1
    assert len(edit.update_nodes) == 1
    assert edit.update_nodes[0].id == "A"
