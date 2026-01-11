import asyncio
from pathlib import Path

from planner_agent.core.orchestrator import default_slice, run_slice
from planner_agent.core.repo import find_repo_root


def test_agent_runner_no_key_noop(monkeypatch):
    # Force "no-key" mode even if OPENAI_API_KEY exists in the shell.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    repo_root = Path(find_repo_root())
    rr = asyncio.run(run_slice(repo_root, default_slice("noop"), workers=2, max_fix_rounds=1))
    assert rr.gates
    assert rr.gates[-1].ok
