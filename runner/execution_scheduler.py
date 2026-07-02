"""
Execution Scheduler — SHRRI AI OS v2 (Phase 4)

Drives a WorkflowGraph to completion. Repeatedly asks the graph for
ready tasks, executes each one, and checkpoints progress after every
step via CheckpointManager — so a crash mid-workflow can resume
instead of losing everything.

Task execution is pluggable via a handlers dict: {task_type: callable}.
The only built-in handler is "llm_call", which routes through
ProviderRouter (respecting Model Selection / Provider Ranking /
Offline First / Hybrid Routing — all of Phase 3 — automatically,
since it just calls the same ProviderRouter everything else uses).

Stops early if any task fails — does not attempt to run further
ready tasks after a failure, since downstream tasks may depend on
correctness we can no longer guarantee.
"""

from runner.workflow_graph import WorkflowGraph
from runner.checkpoint_manager import CheckpointManager
from runner.message_bus import MessageBus
from runner.router_adapter import RouterAdapter as ProviderRouter


def _default_llm_handler(payload: dict, provider_router: ProviderRouter, queue=None) -> str:
    prompt = payload.get("prompt", "")
    capability = payload.get("capability")  # None triggers Model Selection auto-detect

    # Substitute {output_of_<step_id>} placeholders with the actual
    # completed result of that dependency, if the Goal Planner attached
    # a dep_task_ids mapping (step_id -> real task_id) to this payload.
    dep_task_ids = payload.get("dep_task_ids")
    if dep_task_ids and queue is not None:
        for step_id, task_id in dep_task_ids.items():
            dep_task = queue.get(task_id)
            if dep_task and dep_task["status"] == "done":
                placeholder = "{output_of_" + step_id + "}"
                prompt = prompt.replace(placeholder, str(dep_task["result"]))

    result = provider_router.generate(prompt, capability=capability)
    if not result["success"]:
        raise RuntimeError(result.get("error", "unknown provider error"))
    return result["text"]


class ExecutionScheduler:
    def __init__(self, graph: WorkflowGraph, workflow_id: str,
                 checkpoint_manager: CheckpointManager | None = None,
                 provider_router: ProviderRouter | None = None,
                 handlers: dict | None = None, verbose: bool = False,
                 bus: MessageBus | None = None, runtime=None):
        self.graph = graph
        self.workflow_id = workflow_id
        self.checkpoints = checkpoint_manager or CheckpointManager()
        self.provider_router = provider_router or ProviderRouter(web_search=False)
        self.verbose = verbose
        self.bus = bus or MessageBus(workflow_id)
        self.runtime = runtime

        self.handlers = {
            "llm_call": lambda payload: _default_llm_handler(payload, self.provider_router, self.graph.queue),
        }
        if handlers:
            self.handlers.update(handlers)

    def _checkpoint(self):
        tasks = self.graph.queue.all_tasks()
        safe_tasks = []
        for t in tasks:
            t2 = dict(t)
            if isinstance(t2.get("payload"), dict):
                payload2 = dict(t2["payload"])
                payload2.pop("bus", None)
                payload2.pop("runtime", None)
                t2["payload"] = payload2
            safe_tasks.append(t2)
        state = {"tasks": safe_tasks}
        self.checkpoints.save(self.workflow_id, state)

    def run(self) -> dict:
        """
        Runs the workflow to completion (or until a task fails).
        Returns a summary dict: {completed: bool, failed: bool, tasks: [...]}
        """
        if self.verbose:
            print(f"[scheduler] Starting workflow {self.workflow_id}")
        self.bus.publish("workflow_start", {"workflow_id": self.workflow_id})

        while not self.graph.is_complete():
            ready = self.graph.ready_tasks()
            if not ready:
                # No ready tasks but graph isn't complete — either a
                # dependency deadlock (shouldn't happen post cycle-check)
                # or every remaining path is blocked by a failure.
                break

            for task in ready:
                task_id = task["id"]
                self.graph.queue.mark_running(task_id)
                self._checkpoint()

                if self.verbose:
                    print(f"[scheduler] Running task {task_id} ({task['type']})")
                self.bus.publish("task_start", {"task_id": task_id, "type": task["type"]})
                task["payload"]["bus"] = self.bus
                task["payload"]["workflow_id"] = self.workflow_id
                task["payload"]["runtime"] = self.runtime

                handler = self.handlers.get(task["type"])
                if handler is None:
                    self.graph.queue.mark_failed(task_id, f"No handler for task type '{task['type']}'")
                    self._checkpoint()
                    continue

                max_attempts = 2
                last_error = None
                succeeded = False
                for attempt in range(1, max_attempts + 1):
                    try:
                        result = handler(task["payload"])
                        self.graph.queue.mark_done(task_id, result)
                        self.bus.publish("task_done", {"task_id": task_id, "type": task["type"], "result": result})
                        if self.verbose:
                            print(f"[scheduler] Task {task_id} done.")
                        succeeded = True
                        break
                    except Exception as e:
                        last_error = str(e)
                        if attempt < max_attempts:
                            self.bus.publish("task_retry", {"task_id": task_id, "type": task["type"], "attempt": attempt, "error": last_error})
                            if self.verbose:
                                print(f"[scheduler] Task {task_id} attempt {attempt} failed: {last_error} — retrying")
                        else:
                            self.graph.queue.mark_failed(task_id, last_error)
                            self.bus.publish("task_failed", {"task_id": task_id, "type": task["type"], "error": last_error})
                            if self.verbose:
                                print(f"[scheduler] Task {task_id} failed after {attempt} attempts: {last_error}")
                self._checkpoint()

                if self.graph.has_failures():
                    # Stop immediately — don't start more work once
                    # something has failed.
                    break

            if self.graph.has_failures():
                break

        completed = self.graph.is_complete() and not self.graph.has_failures()
        failed = self.graph.has_failures()
        self.bus.publish("workflow_done", {"workflow_id": self.workflow_id, "completed": completed, "failed": failed})

        if completed:
            # Clean up — no need to keep a checkpoint for a finished workflow
            self.checkpoints.delete(self.workflow_id)

        if self.verbose:
            print(f"[scheduler] Workflow {self.workflow_id} finished. completed={completed} failed={failed}")

        return {
            "completed": completed,
            "failed": failed,
            "tasks": self.graph.queue.all_tasks(),
        }
