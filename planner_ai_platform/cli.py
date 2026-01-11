from __future__ import annotations

import typer

from planner_ai_platform.core.errors import PlanError, PlanLoadError, PlanValidationError
from planner_ai_platform.core.expand.expand_plan import dump_plan_yaml, expand_plan_dict
from planner_ai_platform.core.expand.template_config import (
    DEFAULT_TEMPLATES,
    TemplateConfigError,
    load_and_merge,
)
from planner_ai_platform.core.io.load_plan import load_plan
from planner_ai_platform.core.lint.lint_plan import lint_plan
from planner_ai_platform.core.validate.validate_plan import summarize_plan, validate_plan

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback()
def _callback() -> None:
    """Planner CLI."""
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
    _, validation_errors = validate_plan(plan)

    errors = lint_errors + validation_errors
    if errors:
        _print_errors(errors)
        raise typer.Exit(code=2)

    typer.echo("OK: lint passed")


@app.command("templates")
def templates(
    template_file: str | None = typer.Option(
        None,
        "--template-file",
        help="Optional YAML file to add/override templates",
    ),
) -> None:
    """List available deterministic expansion templates (Phase 3)."""
    try:
        templates_map = load_and_merge(template_file)
    except FileNotFoundError:
        _print_errors(
            [
                PlanLoadError(
                    code="E_TEMPLATE_FILE_NOT_FOUND",
                    message=f"template file not found: {template_file}",
                    file=None,
                    path="template_file",
                )
            ]
        )
        raise typer.Exit(code=1)
    except TemplateConfigError as e:
        _print_errors(
            [
                PlanValidationError(
                    code="E_TEMPLATE_FILE_INVALID",
                    message=str(e),
                    file=None,
                    path="template_file",
                )
            ]
        )
        raise typer.Exit(code=2)

    typer.echo("Templates:")
    for name in sorted(templates_map.keys()):
        typer.echo(f"- {name}: {', '.join(templates_map[name])}")


@app.command("expand")
def expand(
    path: str = typer.Argument(..., help="Path to a plan file (.yaml/.yml/.json)"),
    out: str = typer.Option(..., "--out", help="Path to write expanded YAML plan"),
    root: str | None = typer.Option(None, "--root", help="Expand only this OUTCOME node id"),
    template: str = typer.Option(
        "simple",
        "--template",
        help="Expansion template (deterministic): simple|dev|ops",
    ),
    template_file: str | None = typer.Option(
        None,
        "--template-file",
        help="Optional YAML file to add/override templates",
    ),
    mode: str = typer.Option(
        "append",
        "--mode",
        help="Expansion mode: append (default), merge (idempotent), or reconcile (repair)",
    ),
    reconcile_strict: bool = typer.Option(
        True,
        "--reconcile-strict/--reconcile-loose",
        help="In reconcile mode, only reuse tasks already scoped to the chosen deliverable",
    ),
) -> None:
    """Deterministically expand outcome roots into deliverables + tasks (Phase 3)."""
    try:
        plan = load_plan(path)
    except PlanLoadError as e:
        _print_errors([e])
        raise typer.Exit(code=1)

    graph, errors = validate_plan(plan)
    if errors or graph is None:
        _print_errors(errors)
        raise typer.Exit(code=2)

    # Select outcome roots
    if root is not None:
        if root not in graph.nodes_by_id:
            _print_errors(
                [
                    PlanValidationError(
                        code="E_EXPAND_UNKNOWN_ROOT",
                        message=f"--root references unknown id: {root}",
                        file=plan.get("__file__"),
                        path="root",
                    )
                ]
            )
            raise typer.Exit(code=2)
        if graph.nodes_by_id[root].type != "outcome":
            _print_errors(
                [
                    PlanValidationError(
                        code="E_EXPAND_UNSUPPORTED_ROOT_TYPE",
                        message=f"--root must be type=outcome, got type={graph.nodes_by_id[root].type}",
                        file=plan.get("__file__"),
                        path="root",
                    )
                ]
            )
            raise typer.Exit(code=2)
        outcome_roots = [root]
    else:
        outcome_roots = sorted([rid for rid in graph.roots if graph.nodes_by_id[rid].type == "outcome"])
        if not outcome_roots:
            _print_errors(
                [
                    PlanValidationError(
                        code="E_EXPAND_NO_OUTCOME_ROOTS",
                        message="no outcome roots to expand (roots exist, but none are type=outcome)",
                        file=plan.get("__file__"),
                        path="root_ids",
                    )
                ]
            )
            raise typer.Exit(code=2)

    try:
        templates_map = load_and_merge(template_file)
    except FileNotFoundError:
        _print_errors(
            [
                PlanLoadError(
                    code="E_TEMPLATE_FILE_NOT_FOUND",
                    message=f"template file not found: {template_file}",
                    file=plan.get("__file__"),
                    path="template_file",
                )
            ]
        )
        raise typer.Exit(code=1)
    except TemplateConfigError as e:
        _print_errors(
            [
                PlanValidationError(
                    code="E_TEMPLATE_FILE_INVALID",
                    message=str(e),
                    file=plan.get("__file__"),
                    path="template_file",
                )
            ]
        )
        raise typer.Exit(code=2)

    if template not in templates_map:
        _print_errors(
            [
                PlanValidationError(
                    code="E_EXPAND_UNKNOWN_TEMPLATE",
                    message=f"unknown template: {template} (choose one of: {', '.join(sorted(templates_map.keys()))})",
                    file=plan.get("__file__"),
                    path="template",
                )
            ]
        )
        raise typer.Exit(code=2)

    if mode not in ("append", "merge", "reconcile"):
        _print_errors(
            [
                PlanValidationError(
                    code="E_EXPAND_UNKNOWN_MODE",
                    message=f"unknown mode: {mode} (choose one of: append, merge, reconcile)",
                    file=plan.get("__file__"),
                    path="mode",
                )
            ]
        )
        raise typer.Exit(code=2)

    expanded = expand_plan_dict(
        plan,
        outcome_root_ids=outcome_roots,
        template=template,
        templates=templates_map,
        mode=mode,
        reconcile_strict=reconcile_strict,
    )

    # Must pass validate + lint
    g2, v2 = validate_plan(expanded)
    l2 = lint_plan(expanded)
    if v2 or l2 or g2 is None:
        _print_errors(l2 + v2)
        raise typer.Exit(code=2)

    dump_plan_yaml(expanded, out)
    typer.echo(f"OK: wrote expanded plan to {out}")


def _print_errors(errors: list[PlanError]) -> None:
    errors_sorted = sorted(errors, key=lambda e: (e.file or "", e.path or "", e.code))
    for e in errors_sorted:
        typer.echo(str(e), err=True)


def main() -> None:
    app(prog_name="planner")


cli = typer.main.get_command(app)

if __name__ == "__main__":
    main()
