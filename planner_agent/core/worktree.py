from __future__ import annotations

import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Worktree:
    path: Path
    keep: bool = False


def ensure_clean_git(repo_root: Path) -> None:
    """Raise RuntimeError if the repo has uncommitted changes."""
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError("git status failed; is this a git repo?")
    if (proc.stdout or "").strip():
        raise RuntimeError(
            "Repository has uncommitted changes. Commit/stash first, or pass --allow-dirty."
        )


@contextmanager
def temp_worktree(repo_root: Path, prefix: str = "planner-agent-eval-", keep: bool = False):
    """Create a detached git worktree for safe evaluation."""
    base_dir = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        proc = subprocess.run(
            ["git", "worktree", "add", "--detach", str(base_dir), "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "Failed to create git worktree: "
                + ((proc.stdout or "") + (proc.stderr or "")).strip()
            )

        yield Worktree(path=base_dir, keep=keep)
    finally:
        if keep:
            return
        try:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(base_dir)],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
            )
        except Exception:
            pass
        try:
            shutil.rmtree(base_dir, ignore_errors=True)
        except Exception:
            pass
