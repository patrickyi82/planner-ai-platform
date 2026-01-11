from __future__ import annotations

import asyncio
from pathlib import Path

import typer

try:
    from rich.console import Console
    from rich.table import Table
except Exception:  # pragma: no cover
    Console = None  # type: ignore
    Table = None  # type: ignore

from planner_agent.core.orchestrator import default_slice, run_slice
from planner_agent.core.repo import find_repo_root

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console() if Console else None


@app.callback()
def _callback() -> None:
    """planner-agent: local multi-agent runner (job queue + worker pool)."""


@app.command("repomap")
def repomap_cmd(max_files: int = typer.Option(200, help="Max files to list")) -> None:
    """Print a repo inventory for debugging context."""
    repo_root = find_repo_root()
    files: list[str] = []
    for p in repo_root.rglob("*"):
        if p.is_dir():
            continue
        rp = str(p.relative_to(repo_root))
        if rp.startswith((".git/", ".venv/", "venv/", ".idea/")):
            continue
        files.append(rp)

    files = sorted(files)
    console.print("Repo files:")
    for f in files[:max_files]:
        console.print(f"- {f}")
    if len(files) > max_files:
        console.print(f"… and {len(files) - max_files} more")


@app.command("run")
def run_cmd(
    goal: str = typer.Argument(..., help="What should the agents accomplish?"),
    workers: int = typer.Option(3, help="Concurrent workers for proposal generation"),
    max_fix_rounds: int = typer.Option(3, help="Max fixer iterations after a failed gate"),
) -> None:
    """Run a single vertical slice with multiple agents."""

    repo_root = find_repo_root()
    spec = default_slice(goal)

    rr = asyncio.run(run_slice(Path(repo_root), spec, workers=workers, max_fix_rounds=max_fix_rounds))

    if Table and console:
        table = Table(title="planner-agent run")
        table.add_column("Gate")
        table.add_column("OK")
        table.add_column("Exit")
        for g in rr.gates:
            table.add_row(g.name, "yes" if g.ok else "no", str(g.exit_code))
        console.print(table)

        console.print("\nApplied patches:")
        for p in rr.applied_patches:
            console.print(f"- [{p.role}] {p.summary} ({len(p.edits)} files, conf={p.confidence})")

        if not rr.ok:
            console.print("\nRun FAILED. Last gate output:")
            console.print(rr.gates[-1].output)
            raise typer.Exit(code=2)

        console.print("\nRun OK")
        return

    # Fallback (no rich)
    for g in rr.gates:
        print(f"{g.name}: {'OK' if g.ok else 'FAIL'} (exit={g.exit_code})")
    for p in rr.applied_patches:
        print(f"[{p.role}] {p.summary} ({len(p.edits)} files)")
    if not rr.ok:
        print(rr.gates[-1].output)
        raise typer.Exit(code=2)


def main() -> None:
    app(prog_name="planner-agent")


if __name__ == "__main__":
    main()


cli = typer.main.get_command(app)