from planner_ai_platform.core.ai.contracts import EditPlan, UpdateNode
from planner_ai_platform.core.ai.orchestrator import GateResult, ai_expand


class FakeLLM:
    def __init__(self, edits):
        self._edits = edits
        self.calls = 0

    def propose_patch(self, *, context, model):
        e = self._edits[min(self.calls, len(self._edits) - 1)]
        self.calls += 1
        return e


def test_ai_expand_bounded_loop_stops_when_gates_pass():
    plan = {
        "schema_version": "0.1.0",
        "nodes": [
            {
                "id": "A",
                "type": "task",
                "title": "t",
                "depends_on": [],
                "definition_of_done": ["x"],
                "owner": "",
                "estimate_hours": 1,
            }
        ],
    }

    # Gate fails until owner is set
    def gates(p):
        owner = p["nodes"][0].get("owner", "")
        return GateResult(ok=bool(owner), errors=["missing owner"] if not owner else [])

    edit_fix = EditPlan(
        add_nodes=[],
        update_nodes=[UpdateNode(id="A", fields={"owner": "platform"})],
        notes=["set owner"],
    )
    llm = FakeLLM([edit_fix])

    def ctx(p, gate, round_idx):
        return {"round": round_idx, "errors": gate.errors}

    res = ai_expand(
        plan=plan, llm=llm, model="x", build_context=ctx, gates=gates, workers=2, max_fix_rounds=3
    )
    assert res.last_gate.ok
    assert res.rounds == 1
    assert res.plan["nodes"][0]["owner"] == "platform"
