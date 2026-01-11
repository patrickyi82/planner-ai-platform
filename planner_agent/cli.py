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
from planner_agent.core.eval import run_eval

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

    rr = asyncio.run(
        run_slice(Path(repo_root), spec, workers=workers, max_fix_rounds=max_fix_rounds)
    )

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


@app.command("eval")
def eval_cmd(
    suite: Path = typer.Option(..., "--suite", help="Suite file or directory (YAML)"),
    models: list[str] = typer.Option(
        ..., "--model", "-m", help="Model (repeatable): -m gpt-5-mini -m gpt-5.2-pro"
    ),
    runs: int = typer.Option(3, help="Runs per case per model"),
    workers: int = typer.Option(3, help="Concurrent workers for proposal generation"),
    max_fix_rounds: int = typer.Option(3, help="Max fixer iterations after failed gate"),
    out: Path = typer.Option(Path("eval/results.jsonl"), "--out", help="Output JSONL path"),
    allow_dirty: bool = typer.Option(
        False, help="Allow uncommitted changes (only safe with --no-worktrees)"
    ),
    no_worktrees: bool = typer.Option(
        False, "--no-worktrees", help="Run eval in-place (unsafe; modifies your working tree)"
    ),
    keep_worktrees: bool = typer.Option(False, help="Keep worktrees (debugging)"),
) -> None:
    """Benchmark models against a suite; writes JSONL and prints a summary."""
    summary = run_eval(
        suite_path=suite,
        models=models,
        runs=runs,
        workers=workers,
        max_fix_rounds=max_fix_rounds,
        out_jsonl=out,
        allow_dirty=allow_dirty,
        use_worktrees=(not no_worktrees),
        keep_worktrees=keep_worktrees,
    )

    if console and Table:
        table = Table(title=f"planner-agent eval ({summary['cases']} cases)")
        table.add_column("Model")
        table.add_column("Runs")
        table.add_column("Success")
        table.add_column("Avg sec")
        table.add_column("Avg fixes")
        table.add_column("Avg in tok")
        table.add_column("Avg out tok")

        for m, s in summary["summary"].items():
            table.add_row(
                m,
                str(s["runs"]),
                f"{s['success_rate'] * 100:.0f}%",
                f"{s['avg_seconds']:.2f}",
                f"{s['avg_fix_patches']:.2f}",
                f"{s['avg_input_tokens']:.0f}",
                f"{s['avg_output_tokens']:.0f}",
            )
        console.print(table)
        console.print(f"\nWrote: {summary['out']}")
    else:
        print(summary)


def main() -> None:
    app(prog_name="planner-agent")


if __name__ == "__main__":
    main()


cli = typer.main.get_command(app)
