from __future__ import annotations

import typer

from planner_ai_platform.core.errors import PlanError, PlanLoadError
from planner_ai_platform.core.io.load_plan import load_plan
from planner_ai_platform.core.lint.lint_plan import lint_plan
from planner_ai_platform.core.validate.validate_plan import summarize_plan, validate_plan

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback()
def _callback() -> None:
    """Planner CLI."""
    # Having a callback forces Typer into multi-command mode (COMMAND [ARGS]...).
    return


@app.command("validate")
def validate(path: str = typer.Argument(..., help="Path to a plan file (.yaml/.yml/.json)")) -> None:
    """Validate a plan file against schema v0."""
    try:
        plan = load_plan(path)
    except PlanLoadError as e:
        _print_errors([e])
        raise typer.Exit(code=1)

    graph, errors = validate_plan(plan)
    if errors:
        _print_errors(errors)
        raise typer.Exit(code=2)

    assert graph is not None
    typer.echo(summarize_plan(graph))


@app.command("lint")
def lint(path: str = typer.Argument(..., help="Path to a plan file (.yaml/.yml/.json)")) -> None:
    """Lint a plan file (rules beyond minimal schema validation)."""

    try:
        plan = load_plan(path)
    except PlanLoadError as e:
        _print_errors([e])
        raise typer.Exit(code=1)

    lint_errors = lint_plan(plan)

    # Optionally also include schema/validation errors so the user gets a full picture.
    _, validation_errors = validate_plan(plan)

    errors = lint_errors + validation_errors
    if errors:
        _print_errors(errors)
        raise typer.Exit(code=2)

    typer.echo("OK: lint passed")


def _print_errors(errors: list[PlanError]) -> None:
    errors_sorted = sorted(errors, key=lambda e: (e.file or "", e.path or "", e.code))
    for e in errors_sorted:
        typer.echo(str(e), err=True)


def main() -> None:
    # console_scripts entrypoint
    app(prog_name="planner")


if __name__ == "__main__":
    main()

import typer

cli = typer.main.get_command(app)