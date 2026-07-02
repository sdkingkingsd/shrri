"""
Workflow Graph Builder — SHRRI AI OS v2 (Phase 4)

Represents a multi-step goal as a DAG (directed acyclic graph) of
tasks, where each task can depend on others completing first. This
sits above TaskQueue: TaskQueue tracks status of individual tasks,
WorkflowGraph tracks the dependency structure between them and
tells the Execution Scheduler which tasks are ready to run.

A task is "ready" when all of its dependencies have status "done"
in the underlying TaskQueue. Cycle detection is included — a graph
with a circular dependency is invalid and should be rejected at
build time, not discovered mid-execution.
"""

from runner.task_queue import TaskQueue


class CycleError(Exception):
    """Raised when adding a dependency would create a cycle."""
    pass


class WorkflowGraph:
    def __init__(self, queue: TaskQueue | None = None):
        self.queue = queue or TaskQueue()
        # task_id -> set of task_ids it depends on
        self._deps: dict[str, set] = {}

    def add_task(self, task_type: str, payload: dict, depends_on: list[str] | None = None) -> str:
        """
        Add a task to the graph. depends_on is a list of task_ids
        (returned from earlier add_task calls) that must be "done"
        before this task is considered ready.
        """
        task_id = self.queue.add(task_type, payload)
        deps = set(depends_on or [])

        # Validate all dependency ids actually exist in the graph
        for dep_id in deps:
            if dep_id not in self._deps and self.queue.get(dep_id) is None:
                raise ValueError(f"Unknown dependency task_id: {dep_id}")

        self._deps[task_id] = deps

        if self._has_cycle():
            # Roll back — don't leave a broken graph in place
            del self._deps[task_id]
            raise CycleError(f"Adding task {task_id} with deps {deps} would create a cycle")

        return task_id

    def _has_cycle(self) -> bool:
        """DFS-based cycle detection over the current dependency graph."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {tid: WHITE for tid in self._deps}

        def visit(tid):
            color[tid] = GRAY
            for dep in self._deps.get(tid, ()):
                if color.get(dep, WHITE) == GRAY:
                    return True  # back edge -> cycle
                if color.get(dep, WHITE) == WHITE and visit(dep):
                    return True
            color[tid] = BLACK
            return False

        for tid in self._deps:
            if color[tid] == WHITE:
                if visit(tid):
                    return True
        return False

    def ready_tasks(self) -> list[dict]:
        """
        Returns all pending tasks whose dependencies are all 'done'.
        These are safe to hand to the Execution Scheduler right now.
        """
        ready = []
        for task in self.queue.all_tasks():
            if task["status"] != "pending":
                continue
            deps = self._deps.get(task["id"], set())
            if all(self.queue.get(d)["status"] == "done" for d in deps):
                ready.append(task)
        return ready

    def is_complete(self) -> bool:
        """True when every task in the graph has finished (done or failed)."""
        return all(t["status"] in ("done", "failed") for t in self.queue.all_tasks())

    def has_failures(self) -> bool:
        return any(t["status"] == "failed" for t in self.queue.all_tasks())
