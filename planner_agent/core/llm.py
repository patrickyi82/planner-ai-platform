from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class LLMResponse:
    text: str
    raw: Any


def _role_env_key(role: str) -> str:
    """Map a role name to a role-specific env var key.

    Examples:
      - coder -> OPENAI_MODEL_CODER
      - runtime-expand -> OPENAI_MODEL_RUNTIME_EXPAND
    """

    role_key = re.sub(r"[^A-Za-z0-9]+", "_", role).strip("_").upper()
    return f"OPENAI_MODEL_{role_key}"


def model_for_role(role: str, default_model: str) -> str:
    """Return the model to use for a given role.

    Resolution order:
      1) OPENAI_MODEL_<ROLE>
      2) default_model
    """

    override = (os.getenv(_role_env_key(role), "") or "").strip()
    return override or default_model


class LLMClient:
    """Thin wrapper around the OpenAI API (Responses API)."""

    def __init__(self, default_model: str | None = None) -> None:
        self.default_model = default_model or os.getenv("OPENAI_MODEL", "gpt-5-mini")

        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

        # Monitoring hook: how often each model was used.
        self.models_used: dict[str, int] = {}

    def is_configured(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def respond(
        self,
        system: str,
        user: str,
        json_schema: Optional[dict[str, Any]] = None,
        model: str | None = None,
    ) -> LLMResponse:
        """Synchronous call.

        If OPENAI_API_KEY is not set, returns a stub response to keep the runner usable.
        """

        use_model = model or self.default_model
        self.models_used[use_model] = self.models_used.get(use_model, 0) + 1

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
                raw={"disabled": True, "model": use_model},
            )

        from openai import OpenAI  # type: ignore

        client = OpenAI()

        kwargs: dict[str, Any] = {}
        if json_schema is not None:
            # Responses API structured output via JSON schema.
            kwargs["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": json_schema.get("name", "schema"),
                    "strict": True,
                    "schema": json_schema.get("schema", {}),
                }
            }

        response = client.responses.create(
            model=use_model,
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
