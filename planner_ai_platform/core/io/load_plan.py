from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from planner_ai_platform.core.errors import PlanLoadError


def load_plan(path: str) -> dict[str, Any]:
    """Load YAML/JSON plan file.

    Returns a dict with keys: schema_version, nodes, optional root_ids.
    Does not coerce types; validator owns shape checking.
    """

    p = Path(path)
    if not p.exists():
        raise PlanLoadError(
            code="E_FILE_NOT_FOUND",
            message="file does not exist",
            file=str(p),
        )

    suffix = p.suffix.lower()
    try:
        raw_text = p.read_text(encoding="utf-8")
    except Exception as e:  # pragma: no cover
        raise PlanLoadError(code="E_FILE_READ", message=str(e), file=str(p)) from e

    try:
        if suffix in {".yaml", ".yml"}:
            data = yaml.safe_load(raw_text)
        elif suffix == ".json":
            data = json.loads(raw_text)
        else:
            raise PlanLoadError(
                code="E_UNSUPPORTED_FORMAT",
                message="supported formats are .yaml/.yml and .json",
                file=str(p),
            )
    except PlanLoadError:
        raise
    except Exception as e:
        code = "E_YAML_PARSE" if suffix in {".yaml", ".yml"} else "E_JSON_PARSE"
        raise PlanLoadError(code=code, message=str(e), file=str(p)) from e

    if not isinstance(data, dict):
        raise PlanLoadError(
            code="E_INVALID_TOP_LEVEL",
            message="top-level document must be a mapping/object",
            file=str(p),
        )

    # Normalize: keep only expected keys; validator checks required ones.
    normalized: dict[str, Any] = {
        "schema_version": data.get("schema_version"),
        "nodes": data.get("nodes"),
    }
    if "root_ids" in data:
        normalized["root_ids"] = data.get("root_ids")

    normalized["__file__"] = str(p)
    return normalized
