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


DEFAULT_GATES: list[Gate] = [
    Gate(name="pytest", command="python -m pytest -q"),
    Gate(name="planner-validate", command="planner validate examples/basic-plan.yaml"),
]


def _build_env() -> dict[str, str]:
    """Ensure subprocesses use the same venv/interpreter as planner-agent."""
    env = dict(os.environ)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    # Prepend the current interpreter's bin dir so `python` and console scripts
    # (e.g., `planner`) resolve to the same environment.
    bin_dir = str(Path(sys.executable).parent)
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")

    return env


def run_gate(repo_root: Path, gate: Gate, timeout_s: int = 900) -> GateResult:
    env = _build_env()

    # Use sys.executable for pytest so we don't accidentally call system python.
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
        cmd_str = " ".join(["python", "-m", "pytest", "-q"])
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
