from __future__ import annotations

import json
import typer

from planner_ai_platform.core.errors import PlanError, PlanLoadError, PlanValidationError
from planner_ai_platform.core.expand.expand_plan import dump_plan_yaml, expand_plan_dict
from planner_ai_platform.core.expand.template_config import (
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
def validate(
    path: str = typer.Argument(..., help="Path to a plan file (.yaml/.yml/.json)"),
    format: str = typer.Option("text", "--format", help="Output format: text|json"),
) -> None:
    """Validate a plan file against schema v0."""
    if format not in ("text", "json"):
        err = PlanValidationError(
            code="E_VALIDATE_UNKNOWN_FORMAT",
            message=f"unknown format: {format} (choose one of: text, json)",
            file=None,
            path="format",
        )
        _print_errors([err])
        raise typer.Exit(code=2)

    def _to_item(e: PlanError) -> dict:
        source = "load" if isinstance(e, PlanLoadError) else "validate"
        return {
            "code": e.code,
            "message": e.message,
            "file": e.file,
            "path": e.path,
            "severity": "error",
            "source": source,
        }

    def _emit_json(
        ok: bool,
        *,
        exit_code: int,
        schema_version: str | None,
        errors: list[PlanError],
        summary: dict | None,
    ) -> None:
        payload = {
            "tool": "planner",
            "command": "validate",
            "schema_version": schema_version,
            "ok": ok,
            "error_count": len(errors),
            "errors": [_to_item(e) for e in errors],
            "summary": summary,
        }
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        raise typer.Exit(code=exit_code)

    try:
        plan = load_plan(path)
    except PlanLoadError as e:
        if format == "json":
            _emit_json(
                False,
                exit_code=1,
                schema_version=None,
                errors=[e],
                summary=None,
            )
        _print_errors([e])
        raise typer.Exit(code=1)

    graph, errors = validate_plan(plan)
    if errors:
        if format == "json":
            schema_v = (
                plan.get("schema_version") if isinstance(plan.get("schema_version"), str) else None
            )
            _emit_json(
                False,
                exit_code=2,
                schema_version=schema_v,
                errors=errors,
                summary=None,
            )
        _print_errors(errors)
        raise typer.Exit(code=2)

    assert graph is not None

    if format == "text":
        typer.echo(summarize_plan(graph))
        return

    # JSON success output
    from collections import Counter

    counts = Counter([n.type for n in graph.nodes_by_id.values()])
    summary = {
        "node_count": len(graph.nodes_by_id),
        "type_counts": {k: int(v) for k, v in counts.items()},
        "roots": list(graph.roots),
    }

    _emit_json(
        True,
        exit_code=0,
        schema_version=graph.schema_version,
        errors=[],
        summary=summary,
    )


@app.command("lint")
def lint(
    path: str = typer.Argument(..., help="Path to a plan file (.yaml/.yml/.json)"),
    format: str = typer.Option("text", "--format", help="Output format: text|json"),
) -> None:
    """Lint a plan file (rules beyond minimal schema validation)."""
    SDF_VERSION = "v0"

    if format not in ("text", "json"):
        # treat as a validation-style error
        err = PlanValidationError(
            code="E_LINT_UNKNOWN_FORMAT",
            message=f"unknown format: {format} (choose one of: text, json)",
            file=None,
            path="format",
        )
        _print_errors([err])
        raise typer.Exit(code=2)

    def _to_item(e: PlanError) -> dict:
        code = getattr(e, "code", "E_UNKNOWN")
        source = (
            "lint" if code.startswith("L_") else "validate" if code.startswith("E_") else "unknown"
        )
        return {
            "code": e.code,
            "message": e.message,
            "file": e.file,
            "path": e.path,
            "severity": "error",  # Phase 2 currently treats all lint findings as errors
            "source": source,
        }

    def _emit_json(ok: bool, errors: list[PlanError], exit_code: int) -> None:
        payload = {
            "tool": "planner",
            "command": "lint",
            "sdf_version": SDF_VERSION,
            "ok": ok,
            "error_count": len(errors),
            "errors": [_to_item(e) for e in errors],
        }
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        raise typer.Exit(code=exit_code)

    # Load plan
    try:
        plan = load_plan(path)
    except PlanLoadError as e:
        if format == "json":
            _emit_json(False, [e], 1)
        _print_errors([e])
        raise typer.Exit(code=1)

    lint_errors = lint_plan(plan)
    _, validation_errors = validate_plan(plan)
    errors: list[PlanError] = lint_errors + validation_errors

    # Text output
    if format == "text":
        typer.echo(f"SDF {SDF_VERSION}")
        if errors:
            _print_errors(errors)
            raise typer.Exit(code=2)
        typer.echo("OK: lint passed")
        return

    # JSON output
    if errors:
        _emit_json(False, errors, 2)
    _emit_json(True, [], 0)


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
        outcome_roots = sorted(
            [rid for rid in graph.roots if graph.nodes_by_id[rid].type == "outcome"]
        )
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
