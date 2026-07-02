"""
Testing Agent — SHRRI AI OS v2 (Phase 5)

Thin wrapper around two existing pieces of testing infrastructure:
  - test_suite.py — SHRRI's own regression suite (functional + edge
    cases across Gmail, memory, dispatcher, etc). Already safe to run
    repeatedly: uses a throwaway memory DB override and dry-runs sends.
  - tools.code_sandbox.run_code — isolated, network-less, resource-limited
    Docker execution, used to actually run/validate a snippet of code
    the user wants tested (rather than just describing what it would do).

No new test-running or sandboxing logic here.

Intent routing (checked in order):
  - "run the/regression/test suite" / "run all tests" -> execute test_suite.py,
    capture and return its pass/fail summary
  - a fenced code block or "test this code"/"run this" -> extract the code
    and run it through code_sandbox.run_code
  - everything else -> explain what would be tested, asking for either
    a code block to run or confirmation to run the full suite
"""

import re
import subprocess
import sys


_CODE_FENCE_RE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)


class TestingAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def _run_suite(self) -> str:
        result = subprocess.run(
            [sys.executable, "/home/shrridharshan/shrri/test_suite.py"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return output[-3000:] if output.strip() else "Test suite produced no output."

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "").strip()
        low = prompt.lower()
        if self.verbose:
            print(f"[testing_agent] Handling: {prompt[:80]!r}")

        # Run SHRRI's own regression suite
        if re.search(r"\b(regression|test suite|all tests|run the tests)\b", low):
            return self._run_suite()

        # Extract a fenced code block to actually execute
        fence_match = _CODE_FENCE_RE.search(prompt)
        if fence_match:
            from tools.code_sandbox import run_code
            code = fence_match.group(1).strip()
            output = run_code(code)
            return f"Ran the code in an isolated sandbox. Output:\n{output}"

        # "test this: <code>" without fences
        inline_match = re.search(r"\b(?:test|run)\s+(?:this|the following)\s*:?\s*(.+)$", prompt, re.IGNORECASE | re.DOTALL)
        if inline_match and len(inline_match.group(1).strip()) > 5:
            from tools.code_sandbox import run_code
            code = inline_match.group(1).strip()
            output = run_code(code)
            return f"Ran the code in an isolated sandbox. Output:\n{output}"

        # By the time a step reaches this agent, the Goal Planner has already
        # decided it's a "testing" step — so if the prompt itself looks like
        # bare code (no fences, no "test this" prefix, e.g. the planner
        # stripped wrapper text and passed just the snippet), run it as-is
        # rather than bouncing back asking for a format it will never send.
        looks_like_code = bool(re.search(r"\b(def |print\(|import |class |=\s*\d|return )", prompt))
        if looks_like_code:
            from tools.code_sandbox import run_code
            output = run_code(prompt)
            return f"Ran the code in an isolated sandbox. Output:\n{output}"

        return (
            "I can run SHRRI's own regression test suite (say 'run the test suite'), "
            "or execute a specific piece of code you give me in a sandbox — "
            "paste it in a code block and ask me to test/run it."
        )
