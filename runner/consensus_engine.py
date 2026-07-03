"""
ConsensusEngine — SHRRI Phase 6D
Runs the same task through multiple agents and picks the best answer.

Strategy options:
  "majority"  — pick the answer that appears most often (exact or fuzzy match)
  "longest"   — pick the longest non-error response (assumes more detail = better)
  "llm_judge" — ask an LLM to pick the best answer from all responses
  "first"     — first non-error response wins (fast fallback)

Publishes on the workflow MessageBus:
  consensus_start        — task_type + strategy + n_agents
  consensus_agent_result — agent, result (or error)
  consensus_decision     — winner, strategy, all_results
  consensus_failed       — reason (if all agents failed)

Usage:
    ce = ConsensusEngine(runtime, bus, workflow_id, provider_router)
    result = ce.run(
        task_type="research",
        payload={"prompt": "What is the capital of France?"},
        agents=["research", "coding"],   # any registered agent types
        strategy="llm_judge"             # optional, default: "majority"
    )
"""

import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

_ERROR_PREFIXES = ("error", "exception", "failed", "traceback", "none", "")


def _is_error(text: str) -> bool:
    if not text:
        return True
    return str(text).lower().strip().startswith(tuple(_ERROR_PREFIXES[:4]))


def _fuzzy_match(a: str, b: str, threshold: float = 0.7) -> bool:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold


class ConsensusEngine:
    def __init__(self, runtime, bus=None, workflow_id: str = "",
                 provider_router=None):
        """
        runtime        — AgentRuntime (has .call_agent and .handlers)
        bus            — MessageBus for this workflow (optional)
        workflow_id    — for logging / bus scoping
        provider_router — ProviderRouter, needed only for 'llm_judge' strategy
        """
        self.runtime = runtime
        self.bus = bus
        self.workflow_id = workflow_id
        self.provider_router = provider_router

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, task_type: str, payload: dict,
            agents: list[str] | None = None,
            strategy: str = "majority") -> str:
        """
        Run task_type payload through each agent in `agents` and apply
        `strategy` to pick the winner.

        If `agents` is None, uses all handlers registered in the runtime
        (excluding internal types that start with '_').

        Returns the winning response string.
        Raises RuntimeError if all agents fail.
        """
        if agents is None:
            agents = [k for k in self.runtime.handlers if not k.startswith("_")]

        if self.bus:
            self.bus.publish("consensus_start", {
                "task_type": task_type,
                "strategy": strategy,
                "n_agents": len(agents),
            })

        logger.info(f"[consensus] running '{task_type}' across {agents} (strategy={strategy})")

        # --- collect results from every agent ---
        results: list[dict] = []   # {"agent": str, "result": str, "ok": bool}
        for agent in agents:
            try:
                res = self.runtime.call_agent(agent, dict(payload))
                text = str(res) if res is not None else ""
                ok = not _is_error(text)
                results.append({"agent": agent, "result": text, "ok": ok})
                if self.bus:
                    self.bus.publish("consensus_agent_result", {
                        "agent": agent, "result": text, "ok": ok
                    })
                logger.info(f"[consensus] {agent} → ok={ok} len={len(text)}")
            except Exception as e:
                results.append({"agent": agent, "result": str(e), "ok": False})
                if self.bus:
                    self.bus.publish("consensus_agent_result", {
                        "agent": agent, "result": str(e), "ok": False
                    })
                logger.warning(f"[consensus] {agent} raised: {e}")

        good = [r for r in results if r["ok"]]

        if not good:
            msg = "ConsensusEngine: all agents failed — " + \
                  "; ".join(f"{r['agent']}: {r['result'][:80]}" for r in results)
            if self.bus:
                self.bus.publish("consensus_failed", {"reason": msg})
            raise RuntimeError(msg)

        # --- apply strategy ---
        winner_entry = self._apply_strategy(strategy, good, payload)
        winner = winner_entry["result"]

        if self.bus:
            self.bus.publish("consensus_decision", {
                "winner_agent": winner_entry["agent"],
                "strategy": strategy,
                "all_results": results,
            })

        logger.info(f"[consensus] winner → {winner_entry['agent']} (strategy={strategy})")
        return winner

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------

    def _apply_strategy(self, strategy: str, good: list[dict],
                        payload: dict) -> dict:
        if strategy == "majority":
            return self._majority(good)
        elif strategy == "longest":
            return self._longest(good)
        elif strategy == "llm_judge":
            return self._llm_judge(good, payload)
        elif strategy == "first":
            return good[0]
        else:
            logger.warning(f"[consensus] unknown strategy '{strategy}', falling back to 'first'")
            return good[0]

    def _majority(self, good: list[dict]) -> dict:
        """Pick the answer that matches the most other answers (fuzzy)."""
        if len(good) == 1:
            return good[0]

        scores = [0] * len(good)
        for i, a in enumerate(good):
            for j, b in enumerate(good):
                if i != j and _fuzzy_match(a["result"], b["result"]):
                    scores[i] += 1

        best_idx = scores.index(max(scores))
        return good[best_idx]

    def _longest(self, good: list[dict]) -> dict:
        """Pick the longest response — more detail usually means more useful."""
        return max(good, key=lambda r: len(r["result"]))

    def _llm_judge(self, good: list[dict], payload: dict) -> dict:
        """Ask an LLM to pick the best answer. Falls back to 'longest' if no router."""
        if self.provider_router is None:
            logger.warning("[consensus] llm_judge needs provider_router, falling back to longest")
            return self._longest(good)

        options_text = "\n\n".join(
            f"[Agent {i+1}: {r['agent']}]\n{r['result']}"
            for i, r in enumerate(good)
        )
        original_prompt = payload.get("prompt", "(no prompt provided)")

        judge_prompt = (
            f"You are a judge evaluating AI agent responses.\n"
            f"Original task: {original_prompt}\n\n"
            f"Here are {len(good)} responses:\n\n"
            f"{options_text}\n\n"
            f"Reply with ONLY the number of the best response (e.g. '1' or '2'). "
            f"No explanation."
        )

        try:
            res = self.provider_router.generate(judge_prompt, capability="reasoning")
            if res.get("success"):
                text = res["text"].strip()
                # parse "1" or "Agent 1" or "[1]" etc
                for char in text:
                    if char.isdigit():
                        idx = int(char) - 1
                        if 0 <= idx < len(good):
                            return good[idx]
        except Exception as e:
            logger.warning(f"[consensus] llm_judge provider call failed: {e}")

        # fallback
        return self._longest(good)
