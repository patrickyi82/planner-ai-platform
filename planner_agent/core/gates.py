from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from planner_agent.core.contracts import GateResult


@dataclass(frozen=True)
class Gate:
    name: str
    command: str


# Keep commands human-readable; run_gate may special-case execution.
DEFAULT_GATES: list[Gate] = [
    Gate(name="pytest", command="python -m pytest -q"),
    Gate(name="planner-validate", command="planner validate examples/basic-plan.yaml"),
]


def _build_env() -> dict[str, str]:
    """Environment for running gates.

    - Forces pytest to not autoload external plugins (stability)
    - Ensures the current interpreter's bin dir is on PATH
    """

    env = dict(os.environ)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    bin_dir = str(Path(sys.executable).parent)
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")

    return env


def run_gate(repo_root: Path, gate: Gate, timeout_s: int = 900) -> GateResult:
    env = _build_env()

    # Always run pytest using the current interpreter.
    if gate.name == "pytest":
        args = [sys.executable, "-m", "pytest", "-q"]
        proc = subprocess.run(
            args,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
        cmd_str = "python -m pytest -q"

    # Avoid importing Typer for validation gates; call core validate directly.
    elif gate.name == "planner-validate":
        script = (
            "from planner_ai_platform.core.io.load_plan import load_plan;"
            "from planner_ai_platform.core.validate.validate_plan import validate_plan;"
            "p=load_plan('examples/basic-plan.yaml');"
            "g,errs=validate_plan(p);"
            "import sys;"
            "sys.exit(0 if not errs else 2)"
        )
        args = [sys.executable, "-c", script]
        proc = subprocess.run(
            args,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
        cmd_str = "python -c <validate examples/basic-plan.yaml>"

    else:
        proc = subprocess.run(
            gate.command,
            cwd=str(repo_root),
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
        cmd_str = gate.command

    output = (proc.stdout or "") + (proc.stderr or "")
    return GateResult(
        ok=(proc.returncode == 0),
        name=gate.name,
        command=cmd_str,
        exit_code=proc.returncode,
        output=output.strip(),
    )


def run_gates(repo_root: Path, gates: list[Gate] | None = None) -> list[GateResult]:
    results: list[GateResult] = []
    for g in (gates or DEFAULT_GATES):
        results.append(run_gate(repo_root, g))
        if not results[-1].ok:
            break
    return results
