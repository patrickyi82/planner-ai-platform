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
    """Thin wrapper around the OpenAI API (Responses API)."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5-mini")
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def is_configured(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def respond(self, system: str, user: str, json_schema: Optional[dict[str, Any]] = None) -> LLMResponse:
        """Synchronous call.

        If OPENAI_API_KEY is not set, returns a stub response to keep the runner usable.
        """
        if not self.is_configured():
            self.calls += 1
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

        from openai import OpenAI  # type: ignore

        client = OpenAI()

        kwargs: dict[str, Any] = {}
        if json_schema is not None:
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

        self.calls += 1
        self._accumulate_usage(response)

        text = getattr(response, "output_text", None) or ""
        return LLMResponse(text=text, raw=response)

    def _accumulate_usage(self, response: Any) -> None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return

        def get(k: str) -> int:
            if isinstance(usage, dict):
                return int(usage.get(k, 0) or 0)
            return int(getattr(usage, k, 0) or 0)

        self.input_tokens += get("input_tokens")
        self.output_tokens += get("output_tokens")
