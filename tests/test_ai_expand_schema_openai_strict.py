from __future__ import annotations

from typing import Any

from planner_ai_platform.core.ai.openai_client import EDIT_PLAN_JSON_SCHEMA


def _walk(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def test_openai_structured_outputs_schema_is_strict_objects():
    """Guard against regressions.

    OpenAI structured outputs (json_schema) enforces:
    - every object schema must set additionalProperties: false
    - every object schema must have required including all keys in properties

    This test encodes those constraints so we fail fast during unit tests.
    """

    schema = EDIT_PLAN_JSON_SCHEMA["schema"]

    for node in _walk(schema):
        if not isinstance(node, dict):
            continue

        if node.get("type") != "object":
            continue

        assert node.get("additionalProperties") is False

        props = node.get("properties")
        if isinstance(props, dict):
            req = node.get("required")
            assert isinstance(req, list), "object schema must have required list"
            prop_keys = set(props.keys())
            req_keys = set([x for x in req if isinstance(x, str)])
            missing = sorted(prop_keys - req_keys)
            assert not missing, f"required missing keys: {missing}"


def test_add_nodes_requires_at_least_one_item():
    schema = EDIT_PLAN_JSON_SCHEMA["schema"]
    add_nodes = schema["properties"]["add_nodes"]
    assert add_nodes.get("minItems") == 1
