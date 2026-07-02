"""
Browser Agent — SHRRI AI OS v2 (Phase 5)

Thin wrapper around the existing tools/browser_agent.py:browse_agent(),
which does real Playwright-based browsing: opens a URL found in the
task text, extracts page content, and asks the live Router to answer
the task using that content.

This wrapper exists so BrowserAgent has the same .run(payload) shape
as every other Phase 5 agent, for consistent registration with
ManagerAgent / ExecutionScheduler.
"""

from tools.browser_agent import browse_agent


class BrowserAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def run(self, payload: dict) -> str:
        task = payload.get("prompt", "")
        if self.verbose:
            print(f"[browser_agent] Browsing task: {task[:80]!r}")

        result = browse_agent(task)

        if not result or not result.strip():
            raise RuntimeError("Browser agent got an empty result")
        if result.startswith("❌") or result.startswith("Browser error"):
            raise RuntimeError(f"Browser agent failed: {result}")

        return result
