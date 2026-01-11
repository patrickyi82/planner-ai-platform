from pathlib import Path

from planner_agent.core.orchestrator import default_slice, run_slice
from planner_agent.core.repo import find_repo_root


def test_agent_runner_no_key_noop():
    # Without OPENAI_API_KEY, LLMClient returns a no-op patch. Gates should still pass.
    repo_root = Path(find_repo_root())
    rr = __import__("asyncio").run(run_slice(repo_root, default_slice("noop"), workers=2, max_fix_rounds=1))
    assert rr.gates
    assert rr.gates[-1].ok
