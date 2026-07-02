"""
Coding Agent — SHRRI AI OS v2 (Phase 5)

Specialist agent for code writing/debugging/review tasks. Routes
through the "coding" capability (existing candidate list includes
qwen2.5-coder:7b as local fallback). web_search defaults off since
most coding tasks don't need live web data and it avoids wasted
search calls/latency.
"""

from engine.router import Router

_CODING_SYSTEM_PROMPT = (
    "You are a coding specialist. Focus on correctness, clear "
    "explanations, and working code. Use proper formatting "
    "(code blocks with language tags). Explain key decisions "
    "briefly. If debugging, and no error message/traceback was "
    "given, say what additional info you'd need."
)


class CodingAgent:
    def __init__(self, verbose: bool = False):
        self._router = Router()
        self.verbose = verbose

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "")
        if self.verbose:
            print(f"[coding_agent] Coding task: {prompt[:80]!r}")

        response = self._router.chat(
            prompt,
            system=_CODING_SYSTEM_PROMPT,
            web_search=payload.get("web_search", False),
            capability="coding",
        )

        if not response or not response.strip():
            raise RuntimeError("Coding agent got an empty response from all providers")

        return response
