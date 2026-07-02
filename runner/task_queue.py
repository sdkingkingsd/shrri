"""
Task Queue — SHRRI AI OS v2 (Phase 4)

A simple in-memory FIFO queue of tasks with status tracking. Each
task is a dict with at minimum: id, type, payload, status.
Status lifecycle: pending -> running -> done | failed.

This is deliberately minimal — it does NOT know about dependencies
between tasks (that's Workflow Graph Builder's job) or how to
actually execute a task (that's Execution Scheduler's job). This
module only tracks what's queued and its current state.
"""

import uuid
import time


class TaskQueue:
    def __init__(self):
        self._tasks: dict[str, dict] = {}
        self._order: list[str] = []

    def add(self, task_type: str, payload: dict) -> str:
        """Add a new task, returns its id."""
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = {
            "id": task_id,
            "type": task_type,
            "payload": payload,
            "status": "pending",
            "result": None,
            "error": None,
            "created_at": time.time(),
            "started_at": None,
            "finished_at": None,
        }
        self._order.append(task_id)
        return task_id

    def get(self, task_id: str) -> dict | None:
        return self._tasks.get(task_id)

    def next_pending(self) -> dict | None:
        """Returns the oldest still-pending task, or None if queue is empty of pending work."""
        for task_id in self._order:
            task = self._tasks[task_id]
            if task["status"] == "pending":
                return task
        return None

    def mark_running(self, task_id: str):
        task = self._tasks[task_id]
        task["status"] = "running"
        task["started_at"] = time.time()

    def mark_done(self, task_id: str, result):
        task = self._tasks[task_id]
        task["status"] = "done"
        task["result"] = result
        task["finished_at"] = time.time()

    def mark_failed(self, task_id: str, error: str):
        task = self._tasks[task_id]
        task["status"] = "failed"
        task["error"] = error
        task["finished_at"] = time.time()

    def all_tasks(self) -> list[dict]:
        return [self._tasks[tid] for tid in self._order]

    def is_empty(self) -> bool:
        return self.next_pending() is None
