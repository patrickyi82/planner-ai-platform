from planner_ai_platform.core.ai.apply_patch import apply_patch
from planner_ai_platform.core.ai.contracts import AddNode, EditPlan


def test_apply_patch_remaps_conflicting_ids_and_rewrites_deps():
    plan = {
        "schema_version": "0.1.0",
        "nodes": [
            {
                "id": "TSK-001",
                "type": "task",
                "title": "Existing",
                "depends_on": [],
                "definition_of_done": ["x"],
                "owner": "a",
                "estimate_hours": 1,
            },
        ],
    }

    edit = EditPlan(
        add_nodes=[
            AddNode(
                node={
                    "id": "TSK-001",
                    "type": "task",
                    "title": "New",
                    "depends_on": ["TSK-001"],
                    "definition_of_done": ["y"],
                    "owner": "b",
                    "estimate_hours": 2,
                }
            )
        ],
        update_nodes=[],
        notes=[],
    )

    res = apply_patch(plan, edit)
    assert "TSK-001" in res.id_remap
    new_id = res.id_remap["TSK-001"]
    assert new_id != "TSK-001"

    added = [n for n in res.plan["nodes"] if n.get("title") == "New"][0]
    assert added["id"] == new_id
    # depends_on should have been remapped
    assert added["depends_on"] == [new_id]
