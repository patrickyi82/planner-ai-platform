from __future__ import annotations

import subprocess
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


def run_gate(repo_root: Path, gate: Gate, timeout_s: int = 900) -> GateResult:
    proc = subprocess.run(
        gate.command,
        cwd=str(repo_root),
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        env={**__import__("os").environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return GateResult(
        ok=(proc.returncode == 0),
        name=gate.name,
        command=gate.command,
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
