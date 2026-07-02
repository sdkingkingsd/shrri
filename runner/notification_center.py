"""
Notification Center — SHRRI AI OS v2

Decides WHEN and WHAT to notify about (Phase 2 responsibility).
Actual delivery to Android/Desktop is a separate concern that depends
on Device Abstraction Layer (Phase 15) and Output Layer (Phase 16) —
this module only defines the interface and queues notifications until
a real delivery backend is wired in.

STATUS: interface only. Delivery backends (Android push, desktop
notify-send) are NOT implemented yet — see BUILD_TRACKER.md Phase 15/16.
"""

import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Notification:
    title: str
    body: str
    priority: str = "normal"  # "low", "normal", "high"
    created_at: float = field(default_factory=time.time)
    delivered: bool = False


class NotificationCenter:
    def __init__(self, delivery_handler: Optional[Callable[[Notification], bool]] = None):
        """
        delivery_handler: function that actually sends the notification
        somewhere (desktop notify-send, Android push, Telegram message).
        If None, notifications are just queued — nothing is delivered.
        This keeps Phase 2 decoupled from Phase 15/16 delivery backends.
        """
        self.delivery_handler = delivery_handler
        self._queue: list[Notification] = []

    def notify(self, title: str, body: str, priority: str = "normal") -> Notification:
        note = Notification(title=title, body=body, priority=priority)
        self._queue.append(note)

        if self.delivery_handler:
            note.delivered = self.delivery_handler(note)
        # else: stays queued, undelivered — no backend wired in yet

        return note

    def pending(self) -> list[Notification]:
        return [n for n in self._queue if not n.delivered]

    def all_notifications(self) -> list[Notification]:
        return list(self._queue)
