"""
NegotiationEngine — SHRRI Phase 6E
Multi-agent debate: agents answer, see each other's responses, then
revise. Converges on a refined shared answer through rounds of debate.

Unlike ConsensusEngine (pick one winner), NegotiationEngine produces
a synthesized answer that incorporates the best of all agents.

Flow:
  Round 1 — all agents answer independently
  Round 2 — each agent sees all Round 1 answers and revises/critiques
  Round N — repeat until convergence or max_rounds reached
  Final   — judge LLM synthesizes all final-round answers into one

Publishes on MessageBus:
  negotiation_start         — agents, max_rounds
  negotiation_round_start   — round number
  negotiation_agent_result  — agent, round, result
  negotiation_converged     — round at which convergence detected
  negotiation_final         — synthesized result

Usage:
    ne = NegotiationEngine(runtime, provider_router, bus, workflow_id)
    result = ne.run(
        prompt="Should Python use tabs or spaces?",
        agents=["research", "memory"],
        max_rounds=2,
        convergence_threshold=0.85
    )
"""

import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

_ERROR_PREFIXES = ("error", "exception", "failed", "traceback")


def _is_error(text: str) -> bool:
    if not text or not text.strip():
        return True
    return str(text).lower().strip().startswith(_ERROR_PREFIXES)


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _converged(results: list[str], threshold: float) -> bool:
    """Return True if all results are mutually similar above threshold."""
    if len(results) < 2:
        return False
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            if _similarity(results[i], results[j]) < threshold:
                return False
    return True


class NegotiationEngine:
    def __init__(self, runtime, provider_router=None,
                 bus=None, workflow_id: str = ""):
        self.runtime = runtime
        self.provider_router = provider_router
        self.bus = bus
        self.workflow_id = workflow_id

    def _publish(self, topic: str, payload: dict):
        if self.bus:
            self.bus.publish(topic, payload)

    def run(self, prompt: str,
            agents: list[str] | None = None,
            max_rounds: int = 2,
            convergence_threshold: float = 0.85) -> str:
        """
        Run multi-round negotiation across agents.
        Returns the final synthesized answer string.
        """
        if agents is None:
            agents = [k for k in self.runtime.handlers
                      if not k.startswith("_")]

        self._publish("negotiation_start", {
            "agents": agents,
            "max_rounds": max_rounds,
            "prompt": prompt,
        })

        logger.info(f"[negotiation] starting — agents={agents} "
                    f"max_rounds={max_rounds} prompt={prompt[:60]!r}")

        # Store each agent's latest answer across rounds
        current_answers: dict[str, str] = {}

        for round_num in range(1, max_rounds + 1):
            self._publish("negotiation_round_start", {"round": round_num})
            logger.info(f"[negotiation] round {round_num} starting")

            round_answers: dict[str, str] = {}

            for agent in agents:
                # Build payload — Round 1 is plain prompt,
                # Round 2+ includes other agents' previous answers
                if round_num == 1 or not current_answers:
                    payload = {"prompt": prompt}
                else:
                    others = {k: v for k, v in current_answers.items()
                              if k != agent}
                    debate_context = "\n\n".join(
                        f"[{a}'s answer]\n{ans}"
                        for a, ans in others.items()
                    )
                    payload = {
                        "prompt": (
                            f"Original question: {prompt}\n\n"
                            f"Other agents answered:\n{debate_context}\n\n"
                            f"Review their answers critically. You may agree, "
                            f"disagree, or refine. Give your best final answer:"
                        )
                    }

                try:
                    res = self.runtime.call_agent(agent, payload)
                    text = str(res) if res is not None else ""
                    ok = not _is_error(text)
                except Exception as e:
                    text = str(e)
                    ok = False

                if ok:
                    round_answers[agent] = text
                    logger.info(f"[negotiation] r{round_num} {agent} → "
                                f"ok=True len={len(text)}")
                else:
                    logger.warning(f"[negotiation] r{round_num} {agent} "
                                   f"failed: {text[:80]}")

                self._publish("negotiation_agent_result", {
                    "round": round_num,
                    "agent": agent,
                    "result": text,
                    "ok": ok,
                })

            if not round_answers:
                logger.warning(f"[negotiation] round {round_num} — "
                               f"all agents failed")
                continue

            current_answers = round_answers

            # Check convergence after round 2+
            if round_num >= 2:
                good_texts = list(current_answers.values())
                if _converged(good_texts, convergence_threshold):
                    logger.info(f"[negotiation] converged at round {round_num}")
                    self._publish("negotiation_converged",
                                  {"round": round_num})
                    break

        if not current_answers:
            raise RuntimeError(
                "NegotiationEngine: all agents failed in all rounds"
            )

        # Final synthesis — ask judge LLM to merge all final answers
        final = self._synthesize(prompt, current_answers)

        self._publish("negotiation_final", {
            "result": final,
            "contributing_agents": list(current_answers.keys()),
        })

        logger.info(f"[negotiation] done — final len={len(final)}")
        return final

    def _synthesize(self, original_prompt: str,
                    answers: dict[str, str]) -> str:
        """
        Ask judge LLM to synthesize all agents' final answers into one.
        Falls back to longest answer if no router available.
        """
        if not self.provider_router:
            logger.warning("[negotiation] no router — "
                           "falling back to longest answer")
            return max(answers.values(), key=len)

        options = "\n\n".join(
            f"[{agent}]\n{ans}" for agent, ans in answers.items()
        )

        synth_prompt = (
            f"You are a synthesis expert. Multiple AI agents debated "
            f"the following question:\n\n"
            f"Question: {original_prompt}\n\n"
            f"Their final answers after debate:\n\n"
            f"{options}\n\n"
            f"Synthesize these into ONE comprehensive, accurate, "
            f"well-structured answer. Incorporate the best points "
            f"from each agent. Do not just pick one — merge them."
        )

        try:
            res = self.provider_router.generate(
                synth_prompt, capability="reasoning"
            )
            if res.get("success") and res.get("text", "").strip():
                return res["text"].strip()
        except Exception as e:
            logger.warning(f"[negotiation] synthesis failed: {e}")

        # Fallback to longest
        return max(answers.values(), key=len)
