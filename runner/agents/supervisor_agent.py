"""
Supervisor Agent — SHRRI Phase 6C
Watches a workflow's MessageBus for trouble and reacts in real time,
instead of the user only finding out when the whole goal finishes.
Currently handles:
  - task_failed  -> sends an immediate Telegram alert with the task
                    type and error (only fires after retries are
                    exhausted, since ExecutionScheduler already
                    retries once before publishing task_failed).
Attach it to any workflow's bus via SupervisorAgent(bus).attach() —
it just subscribes; it doesn't own or block the workflow.
"""
import logging
from tools.telegram_notify import send_message

logger = logging.getLogger(__name__)

class SupervisorAgent:
    def __init__(self, bus, verbose: bool = False):
        self.bus = bus
        self.verbose = verbose

    def attach(self):
        """Start listening on the bus. Call once per workflow."""
        self.bus.subscribe("task_failed", self._on_task_failed)

    def _on_task_failed(self, event: dict):
        payload = event.get("payload", {})
        task_type = payload.get("type", "unknown")
        error = payload.get("error", "unknown error")
        workflow_id = event.get("wf", "unknown")
        msg = (
            f"⚠️ SHRRI workflow step failed\n"
            f"Workflow: {workflow_id}\n"
            f"Step type: {task_type}\n"
            f"Error: {error}"
        )
        if self.verbose:
            print(f"[supervisor_agent] Alerting on task_failed: {task_type} — {error}")
        try:
            send_message(msg)
        except Exception as e:
            logger.error(f"[supervisor_agent] Failed to send Telegram alert: {e}")
