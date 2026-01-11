from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PlanError(Exception):
    """Base error envelope. Prefer returning/printing these rather than raising raw exceptions."""

    code: str
    message: str
    file: Optional[str] = None
    path: Optional[str] = None

    def __str__(self) -> str:
        parts: list[str] = []
        if self.file:
            parts.append(self.file)
        if self.path:
            parts.append(self.path)
        loc = ":".join(parts) if parts else "<plan>"
        return f"{loc}: {self.code}: {self.message}"


class PlanLoadError(PlanError):
    pass


class PlanValidationError(PlanError):
    pass
