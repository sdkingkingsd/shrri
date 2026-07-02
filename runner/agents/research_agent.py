"""
Research Agent — SHRRI AI OS v2 (Phase 5)

Specialist agent for factual/research questions. Thin wrapper —
the real work (web search context injection, tool dispatch) already
lives in engine.router.Router (via _get_search_context /
_get_tool_context, triggered automatically when web_search=True).

This agent's job is just to make sure research-type tasks always
get web_search=True and a capability biased toward thorough,
well-cited answers, regardless of what the Goal Planner's prompt
text happened to say.
"""

from engine.router import Router

_RESEARCH_SYSTEM_PROMPT = (
    "You are a research specialist. Be thorough and precise. "
    "If live search results are provided, use them and prefer them "
    "over your own prior knowledge for anything time-sensitive. "
    "If you're uncertain about something, say so rather than "
    "guessing confidently."
)


class ResearchAgent:
    def __init__(self, verbose: bool = False):
        self._router = Router()
        self.verbose = verbose

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "")
        if self.verbose:
            print(f"[research_agent] Researching: {prompt[:80]!r}")

        response = self._router.chat(
            prompt,
            system=_RESEARCH_SYSTEM_PROMPT,
            web_search=True,
            capability="reasoning",
        )

        if not response or not response.strip():
            raise RuntimeError("Research agent got an empty response from all providers")

        return response
