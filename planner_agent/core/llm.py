from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class LLMResponse:
    text: str
    raw: Any


class LLMClient:
    """Thin wrapper around the OpenAI API.

    Uses the Responses API. For Structured Outputs, Responses uses `text.format` (not `response_format`).
    """

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5-mini")

    def is_configured(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def respond(self, system: str, user: str, json_schema: Optional[dict[str, Any]] = None) -> LLMResponse:
        """Synchronous call.

        If OPENAI_API_KEY is not set, returns a stub response to keep the runner usable.
        """

        if not self.is_configured():
            return LLMResponse(
                text=json.dumps(
                    {
                        "summary": "LLM disabled (OPENAI_API_KEY not set). No-op patch.",
                        "edits": [],
                        "confidence": 0.0,
                    }
                ),
                raw={"disabled": True},
            )

        # Import only when needed so the repo works without the agents extra.
        from openai import OpenAI  # type: ignore

        client = OpenAI()

        kwargs: dict[str, Any] = {}
        if json_schema is not None:
            # Responses API structured outputs: text.format
            # Expected shape:
            # text={"format": {"type":"json_schema", "name":..., "strict": True, "schema": {...}}}
            kwargs["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": json_schema.get("name", "schema"),
                    "strict": True,
                    "schema": json_schema.get("schema", {}),
                }
            }

        response = client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            **kwargs,
        )

        text = getattr(response, "output_text", None) or ""
        return LLMResponse(text=text, raw=response)
