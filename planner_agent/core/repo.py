from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepoSnapshot:
    root: Path

    def read_text(self, rel_path: str) -> str:
        return (self.root / rel_path).read_text(encoding="utf-8")

    def list_files(self) -> list[str]:
        out: list[str] = []
        for p in self.root.rglob("*"):
            if p.is_dir():
                continue
            rp = str(p.relative_to(self.root))
            if _should_ignore(rp):
                continue
            out.append(rp)
        return sorted(out)


def _should_ignore(rel_path: str) -> bool:
    # Keep it simple for v0: ignore venv/git caches and large binary-ish folders.
    ignore_prefixes = (
        ".git/",
        ".venv/",
        "venv/",
        ".idea/",
        "__pycache__/",
        "pytest_cache/",
        ".tox/",
        ".cache/",
    )
    return rel_path.startswith(ignore_prefixes)


def find_repo_root(start: str | None = None) -> Path:
    p = Path(start or os.getcwd()).resolve()
    for parent in [p] + list(p.parents):
        if (parent / ".git").exists():
            return parent
    return p
