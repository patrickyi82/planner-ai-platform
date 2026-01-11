from __future__ import annotations

from dataclasses import dataclass

from planner_agent.core.repo import RepoSnapshot


@dataclass(frozen=True)
class RepoMap:
    """A small, LLM-friendly inventory of the repo."""

    files: list[str]

    def to_text(self, max_files: int = 250) -> str:
        shown = self.files[:max_files]
        more = len(self.files) - len(shown)
        lines = ["Repo files:"] + [f"- {p}" for p in shown]
        if more > 0:
            lines.append(f"… and {more} more")
        return "\n".join(lines)


def build_repomap(snapshot: RepoSnapshot) -> RepoMap:
    return RepoMap(files=snapshot.list_files())
