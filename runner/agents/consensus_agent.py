"""
Consensus Agent — SHRRI Phase 6D
Thin handler wrapper around ConsensusEngine so it can be registered
in registry.py like every other agent.

Payload keys:
  prompt     — the question/task to run through multiple agents
  agents     — list of agent types to consult (default: ["research", "coding"])
  strategy   — "majority" | "longest" | "llm_judge" | "first" (default: "longest")
"""
import logging
from runner.consensus_engine import ConsensusEngine

logger = logging.getLogger(__name__)

class ConsensusAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def run(self, payload: dict) -> str:
        runtime  = payload.get("runtime")
        bus      = payload.get("bus")
        wid      = payload.get("workflow_id", "")
        prompt   = payload.get("prompt", "")
        agents   = payload.get("agents", ["research", "coding"])
        strategy = payload.get("strategy", "longest")

        if runtime is None:
            return "ERROR: ConsensusAgent needs runtime (AgentRuntime) in payload."

        if self.verbose:
            logger.info(f"[consensus_agent] prompt={prompt!r} agents={agents} strategy={strategy}")

        ce = ConsensusEngine(runtime, bus=bus, workflow_id=wid)
        return ce.run(
            task_type="consensus_inner",
            payload={"prompt": prompt},
            agents=agents,
            strategy=strategy,
        )
