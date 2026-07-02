"""
Linux Agent — SHRRI AI OS v2 (Phase 5)

Thin wrapper around the existing tools.system_tool.system_control(),
which already does real subprocess-level system control: screen lock,
shutdown/restart (immediate, delayed, or cancelled), volume, and
brightness. No new system-control logic here — just routing the
task prompt straight into the real function and surfacing its result
(including its own "GAP:" messages for unrecognized commands).
"""

from tools.system_tool import system_control


class LinuxAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "").strip()
        if self.verbose:
            print(f"[linux_agent] Handling: {prompt[:80]!r}")

        result = system_control(prompt)
        if not result or not result.strip():
            raise RuntimeError("Linux agent got an empty result")
        return result
