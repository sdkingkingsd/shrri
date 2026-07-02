"""
Scratchpad — SHRRI Phase 6D
Shared key-value state scoped per workflow_id. Lets any agent leave
a note ("here's what I found") that any other agent in the same
workflow can read — even ones not directly downstream in the DAG,
unlike {output_of_<step_id>} substitution which only sees the direct
dependency chain.
Thread-safe. Deliberately simple: just get/set/all, no history or
versioning — that's what MessageBus is for if an audit trail matters.
"""
import threading
import logging

logger = logging.getLogger(__name__)

class Scratchpad:
    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self._data: dict = {}
        self._lock = threading.Lock()

    def set(self, key: str, value) -> None:
        with self._lock:
            self._data[key] = value
        logger.debug(f"[scratchpad:{self.workflow_id}] set '{key}'")

    def get(self, key: str, default=None):
        with self._lock:
            return self._data.get(key, default)

    def all(self) -> dict:
        with self._lock:
            return dict(self._data)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)
