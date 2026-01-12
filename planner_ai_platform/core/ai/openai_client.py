from __future__ import annotations

import json
import os
from typing import Any

from planner_ai_platform.core.ai.contracts import EditPlan, parse_edit_plan


SYSTEM_PROMPT = """You are an assistant for planner-ai-platform.

You MUST output an edit plan JSON object with fields:
- add_nodes: [{"node": {...}}]
- update_nodes: [{"id": "...", "fields": {...}}]
- notes: ["..."]

Return ONLY the JSON edit plan (no markdown, no extra text).

Phase 4 goal: EXPAND the plan using the provided template steps.
Even if the plan is already valid, you MUST propose at least one change.

Rules:
- Prefer adding missing tasks for the selected template steps.
- Use unique IDs consistent with the existing plan's style.
- For tasks: include owner (non-empty), estimate_hours (>0), and non-empty definition_of_done.
- Keep DAG correctness (no dependency cycles).
- Keep nodes reachable from roots.

IMPORTANT: add_nodes MUST contain at least 1 new node.
"""


# OpenAI Structured Outputs requirements:
# - For ALL object schemas, `additionalProperties` MUST be present and MUST be false.
# - For ALL object schemas, `required` MUST include EVERY key in `properties`.
# Therefore we:
# - Enumerate plan node fields explicitly
# - Mark every property as required
# - Use nullable types (e.g., ["string", "null"]) for optional fields


NODE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string"},
        "type": {
            "type": "string",
            "enum": ["outcome", "deliverable", "milestone", "task", "check"],
        },
        "title": {"type": "string"},
        "definition_of_done": {
            "type": "array",
            "items": {"type": "string"},
        },
        "depends_on": {
            "type": "array",
            "items": {"type": "string"},
        },
        # Optional in the plan schema, but required in structured output schema.
        "owner": {"type": ["string", "null"]},
        "estimate_hours": {"type": ["number", "null"]},
        "priority": {"type": ["integer", "null"]},
    },
    # Required must include ALL keys in properties.
    "required": [
        "id",
        "type",
        "title",
        "definition_of_done",
        "depends_on",
        "owner",
        "estimate_hours",
        "priority",
    ],
}


FIELDS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": ["string", "null"]},
        "definition_of_done": {
            "type": ["array", "null"],
            "items": {"type": "string"},
        },
        "depends_on": {
            "type": ["array", "null"],
            "items": {"type": "string"},
        },
        "owner": {"type": ["string", "null"]},
        "estimate_hours": {"type": ["number", "null"]},
        "priority": {"type": ["integer", "null"]},
    },
    # Required must include ALL keys in properties.
    "required": [
        "title",
        "definition_of_done",
        "depends_on",
        "owner",
        "estimate_hours",
        "priority",
    ],
}


EDIT_PLAN_JSON_SCHEMA: dict[str, Any] = {
    "name": "edit_plan",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "add_nodes": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"node": NODE_SCHEMA},
                    "required": ["node"],
                },
            },
            "update_nodes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "fields": FIELDS_SCHEMA,
                    },
                    "required": ["id", "fields"],
                },
                "default": [],
            },
            "notes": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
            },
        },
        # Required must include ALL keys in properties.
        "required": ["add_nodes", "update_nodes", "notes"],
    },
}


class OpenAIPatchClient:
    def __init__(self, *, base_url: str | None = None) -> None:
        self._base_url = base_url

    def propose_patch(self, *, context: dict[str, Any], model: str) -> EditPlan:
        """Propose an EditPlan using OpenAI Responses API structured outputs."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "openai package not installed; install with: pip install openai"
            ) from e

        client = OpenAI(base_url=self._base_url) if self._base_url else OpenAI()

        resp = client.responses.create(
            model=model,
            temperature=0,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _render_user_prompt(context)},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": EDIT_PLAN_JSON_SCHEMA["name"],
                    "schema": EDIT_PLAN_JSON_SCHEMA["schema"],
                    "strict": True,
                }
            },
        )

        raw_text = _extract_output_text(resp)
        try:
            obj = json.loads(raw_text)
        except Exception as e:
            snippet = raw_text[:800]
            raise RuntimeError(f"Failed to parse model JSON. First 800 chars: {snippet}") from e

        return parse_edit_plan(obj)


def _extract_output_text(resp: Any) -> str:
    """Extract response text robustly across OpenAI SDK response shapes."""
    raw = getattr(resp, "output_text", None)
    if isinstance(raw, str) and raw.strip():
        return raw

    dump = None
    if hasattr(resp, "model_dump"):
        try:
            dump = resp.model_dump()
        except Exception:
            dump = None

    if isinstance(dump, dict):
        out = dump.get("output")
        if isinstance(out, list):
            texts: list[str] = []
            for item in out:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for c in content:
                    if not isinstance(c, dict):
                        continue
                    t = c.get("text")
                    if isinstance(t, str) and t.strip():
                        texts.append(t)
            if texts:
                return "\n".join(texts)

    out2 = getattr(resp, "output", None)
    if isinstance(out2, list):
        texts2: list[str] = []
        for item in out2:
            content = getattr(item, "content", None)
            if isinstance(content, list):
                for c in content:
                    t = getattr(c, "text", None)
                    if isinstance(t, str) and t.strip():
                        texts2.append(t)
        if texts2:
            return "\n".join(texts2)

    return str(resp)


def _render_user_prompt(context: dict[str, Any]) -> str:
    # Simple hard constraint reminder.
    hint = (
        "IMPORTANT: add_nodes must contain at least ONE new node. "
        "If you set optional fields, use null (not empty object)."
    )
    return (
        "CONTEXT_JSON:\n"
        + json.dumps(context, indent=2, sort_keys=True)
        + "\n\n"
        + hint
        + "\nReturn only the JSON edit plan."
    )
