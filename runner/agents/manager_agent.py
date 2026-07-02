"""
Manager Agent — SHRRI AI OS v2 (Phase 5)

Top-level orchestrator. Given a raw user goal, this:
1. Calls GoalPlanner to decompose it into a WorkflowGraph
2. Registers all available specialist agents as ExecutionScheduler
   handlers, keyed by task type
3. Runs the scheduler to completion
4. Returns the final result

Specialist agents plug in via register_agent() — this file doesn't
hardcode which agents exist, so Phase 5 agents can be added
incrementally without editing this file each time.
"""

from runner.goal_planner import plan_goal
from runner.execution_scheduler import ExecutionScheduler
from runner.message_bus import MessageBus
from runner.agent_runtime import AgentRuntime
from runner.agents.supervisor_agent import SupervisorAgent
from runner.scratchpad import Scratchpad
from runner.checkpoint_manager import CheckpointManager
import uuid


class ManagerAgent:
    def __init__(self, checkpoint_manager: CheckpointManager | None = None, verbose: bool = False):
        self.checkpoints = checkpoint_manager or CheckpointManager()
        self.verbose = verbose
        self._agent_handlers: dict = {}

    def register_agent(self, task_type: str, handler_fn):
        """
        Register a specialist agent's handler under a task type.
        handler_fn takes a payload dict and returns a result (any
        JSON-serializable value) — same contract as ExecutionScheduler
        handlers generally.
        """
        self._agent_handlers[task_type] = handler_fn
        if self.verbose:
            print(f"[manager_agent] Registered agent for task type '{task_type}'")

    def run_goal(self, goal: str) -> dict:
        """
        Full pipeline: goal -> plan -> execute -> result.
        Returns the ExecutionScheduler's result dict:
        {completed, failed, tasks}
        """
        workflow_id = f"goal_{uuid.uuid4().hex[:8]}"

        if self.verbose:
            print(f"[manager_agent] Planning goal: {goal!r}")

        graph, id_map = plan_goal(goal, verbose=self.verbose)

        bus = MessageBus(workflow_id)
        supervisor = SupervisorAgent(bus, verbose=self.verbose)
        supervisor.attach()
        runtime = AgentRuntime(self._agent_handlers, bus=bus, workflow_id=workflow_id)
        scratchpad = Scratchpad(workflow_id)
        scheduler = ExecutionScheduler(
            graph,
            workflow_id=workflow_id,
            checkpoint_manager=self.checkpoints,
            handlers=self._agent_handlers,
            verbose=self.verbose,
            bus=bus,
            runtime=runtime,
            scratchpad=scratchpad,
        )

        if self.verbose:
            print(f"[manager_agent] Executing workflow {workflow_id}")

        result = scheduler.run()
        result["workflow_id"] = workflow_id
        result["bus"] = bus
        result["runtime"] = runtime
        result["scratchpad"] = scratchpad
        return result
