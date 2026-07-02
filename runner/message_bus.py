"""
MessageBus — SHRRI Phase 6A
Lightweight in-process pub/sub, scoped per workflow_id.
Thread-safe. Callbacks run synchronously in the publisher's thread.
"""
import threading
import logging
from collections import defaultdict
from typing import Callable, Any

logger = logging.getLogger(__name__)

class MessageBus:
    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self._subs: dict = defaultdict(list)
        self._history: list = []
        self._lock = threading.Lock()

    def subscribe(self, topic: str, callback: Callable[[dict], Any]) -> None:
        """Subscribe to a topic. Use topic="*" to receive every event."""
        with self._lock:
            self._subs[topic].append(callback)
        logger.debug(f"[bus:{self.workflow_id}] subscribed to '{topic}'")

    def publish(self, topic: str, payload: dict) -> None:
        event = {"topic": topic, "payload": payload, "wf": self.workflow_id}
        with self._lock:
            self._history.append(event)
            cbs = list(self._subs.get(topic, [])) + list(self._subs.get("*", []))
        logger.info(f"[bus:{self.workflow_id}] '{topic}' -> {len(cbs)} subscriber(s)")
        for cb in cbs:
            try:
                cb(event)
            except Exception as exc:
                logger.error(f"[bus] subscriber error on '{topic}': {exc}")

    def history(self, topic=None) -> list:
        with self._lock:
            if topic:
                return [e for e in self._history if e["topic"] == topic]
            return list(self._history)

    def latest(self, topic: str):
        h = self.history(topic)
        return h[-1] if h else None
