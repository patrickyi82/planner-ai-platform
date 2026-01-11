from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_TEMPLATES: dict[str, list[str]] = {
    # Phase 3 baseline: keep this stable for golden tests.
    "simple": ["Design", "Implement", "Test", "Docs"],
    # Slightly richer dev lifecycle.
    "dev": ["Design", "Implement", "Test", "Docs", "Review", "Release"],
    # Ops-focused expansion.
    "ops": ["Monitoring", "SLOs", "Runbooks", "Playbooks", "Reliability"],
}


class TemplateConfigError(ValueError):
    pass


def load_template_file(path: str | Path) -> dict[str, list[str]]:
    """Load templates from a YAML file.

    Format:
      <name>: ["Task1", "Task2", ...]

    Returns a mapping of template name -> list of task titles.
    """
    p = Path(path)
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise TemplateConfigError("template file must be a mapping of name -> list[str]")

    out: dict[str, list[str]] = {}
    for k, v in raw.items():
        if not isinstance(k, str) or not k.strip():
            raise TemplateConfigError("template names must be non-empty strings")
        if not isinstance(v, list) or not v:
            raise TemplateConfigError(f"template '{k}' must be a non-empty list")
        titles: list[str] = []
        for item in v:
            if not isinstance(item, str) or not item.strip():
                raise TemplateConfigError(f"template '{k}' items must be non-empty strings")
            titles.append(item.strip())
        out[k.strip()] = titles
    return out


def merged_templates(overrides: dict[str, list[str]] | None = None) -> dict[str, list[str]]:
    """Return DEFAULT_TEMPLATES merged with optional overrides.

    Overrides replace templates of the same name, and may add new ones.
    """
    merged = dict(DEFAULT_TEMPLATES)
    if overrides:
        for k, v in overrides.items():
            merged[k] = list(v)
    return merged


def load_and_merge(template_file: str | None) -> dict[str, list[str]]:
    if not template_file:
        return merged_templates()
    overrides = load_template_file(template_file)
    return merged_templates(overrides)
