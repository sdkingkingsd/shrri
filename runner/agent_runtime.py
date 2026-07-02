"""
AgentRuntime — SHRRI Phase 6B
Lets any agent handler call another registered agent as a synchronous
sub-task, mid-execution. Wraps the same handlers dict ManagerAgent
builds via register_agent() — no separate registry, single source
of truth.
Publishes agent_call_start / agent_call_done (or agent_call_failed)
on the workflow's MessageBus so nested calls are visible in bus
history, same as top-level scheduler tasks.
"""
import logging

logger = logging.getLogger(__name__)

class AgentRuntime:
    def __init__(self, handlers: dict, bus=None, workflow_id: str = ""):
        self.handlers = handlers
        self.bus = bus
        self.workflow_id = workflow_id

    def call_agent(self, task_type: str, payload: dict):
        """
        Synchronously invoke another registered agent's handler.
        Raises KeyError if task_type isn't registered.
        Returns whatever that agent's handler returns.
        """
        handler = self.handlers.get(task_type)
        if handler is None:
            raise KeyError(f"No agent registered for task type '{task_type}'")

        call_payload = dict(payload)
        call_payload.setdefault("bus", self.bus)
        call_payload.setdefault("workflow_id", self.workflow_id)
        call_payload.setdefault("runtime", self)

        if self.bus:
            self.bus.publish("agent_call_start", {"type": task_type})
        try:
            result = handler(call_payload)
            if self.bus:
                self.bus.publish("agent_call_done", {"type": task_type, "result": result})
            return result
        except Exception as e:
            if self.bus:
                self.bus.publish("agent_call_failed", {"type": task_type, "error": str(e)})
            logger.error(f"[agent_runtime] '{task_type}' call failed: {e}")
            raise
