from __future__ import annotations

from pathlib import Path

from planner_agent.core.contracts import Patch


def apply_patch(repo_root: Path, patch: Patch) -> None:
    """Apply by writing full file contents.

    v0 strategy: full file writes are deterministic and easier to validate.
    Later we can introduce diffs.
    """

    for edit in patch.edits:
        path = repo_root / edit.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(edit.content, encoding="utf-8")
