"""
Router Adapter — SHRRI AI OS v2 (Phase 4.5 — unify on one engine)

Wraps the live, battle-tested engine.router.Router (web search, tool
dispatch, per-key cooldowns, timeout handling, templlm last-resort
fallback) behind the same interface ProviderRouter exposes, so
GoalPlanner / ExecutionScheduler / future Phase 5 agents can all run
through the SAME engine that already answers real WhatsApp messages
— instead of the newer, thinner ProviderRouter/multi_router stack
that lacks web search and tool dispatch.

This does NOT modify engine/router.py at all — purely additive,
same philosophy as every other adapter in this codebase
(runner/provider_router.py wraps multi_router the same way).
"""

from engine.router import Router
from runner.model_selector import classify as _classify


class RouterAdapter:
    """
    Drop-in replacement for ProviderRouter with the same .generate()
    signature, but backed by the live engine.router.Router instead.
    """

    def __init__(self, web_search: bool = True, verbose: bool = False):
        self._router = Router()
        self.web_search = web_search
        self.verbose = verbose

    def generate(self, prompt: str, capability: str | None = None) -> dict:
        # Mirror ProviderRouter's behavior: if no capability given,
        # infer one via Model Selection (Phase 3) instead of relying
        # solely on Router's own task="default" bucket.
        cap = capability or _classify(prompt)
        # Planner prompts are long structured text — force conversation if classify returns writing/medical/finance which hit unreliable providers
        if cap in ("writing", "medical", "finance") and len(prompt) > 300:
            cap = "conversation"

        try:
            response = self._router.chat(
                prompt,
                capability=cap,
                web_search=self.web_search,
            )
            if not response or not response.strip():
                return {
                    "success": False,
                    "text": None,
                    "error": "Router returned empty response after exhausting all providers/fallbacks",
                }
            return {
                "success": True,
                "text": response,
                "provider": None,   # Router doesn't currently surface which provider won
                "model": None,
            }
        except Exception as e:
            return {
                "success": False,
                "text": None,
                "error": str(e),
            }
