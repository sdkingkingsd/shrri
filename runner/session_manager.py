"""
Session Manager — SHRRI AI OS v2

Tracks one session per (channel, peer_id). Foundation for per-channel
agent isolation. Now supports loading from persistence on startup and
tier upgrades (for DM pairing approval).
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Session:
    session_id: str
    channel: str
    peer_id: str
    permission_tier: str = "restricted"
    history: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    workflow_state: Optional[dict] = None

    def touch(self):
        self.last_active = time.time()

    def add_turn(self, role: str, content: str):
        self.history.append({"role": role, "content": content, "ts": time.time()})
        self.touch()


class SessionManager:
    def __init__(self, main_peer_ids: Optional[dict] = None, store=None):
        self._sessions: dict[tuple, Session] = {}
        self.main_peer_ids = main_peer_ids or {}
        self.store = store  # SessionStore instance, optional
        if self.store:
            self._load_from_store()

    def _load_from_store(self):
        for row in self.store.load_all():
            key = (row["channel"], row["peer_id"])
            self._sessions[key] = Session(
                session_id=row["session_id"],
                channel=row["channel"],
                peer_id=row["peer_id"],
                permission_tier=row["permission_tier"],
                history=row["history"],
                created_at=row["created_at"],
                last_active=row["last_active"],
                workflow_state=row["workflow_state"],
            )

    def _key(self, channel: str, peer_id: str) -> tuple:
        return (channel, peer_id)

    def get_or_create(self, channel: str, peer_id: str) -> Session:
        key = self._key(channel, peer_id)
        if key not in self._sessions:
            tier = "main" if self.main_peer_ids.get(channel) == peer_id else "restricted"
            self._sessions[key] = Session(
                session_id=str(uuid.uuid4()),
                channel=channel,
                peer_id=peer_id,
                permission_tier=tier,
            )
        else:
            self._sessions[key].touch()
        self._persist(key)
        return self._sessions[key]

    def upgrade_to_main(self, channel: str, peer_id: str) -> bool:
        key = self._key(channel, peer_id)
        session = self._sessions.get(key)
        if not session:
            return False
        session.permission_tier = "main"
        self._persist(key)
        return True

    def get(self, channel: str, peer_id: str) -> Optional[Session]:
        return self._sessions.get(self._key(channel, peer_id))

    def all_sessions(self):
        return list(self._sessions.values())

    def prune_inactive(self, max_idle_seconds: int = 3600):
        now = time.time()
        dead = [k for k, s in self._sessions.items() if now - s.last_active > max_idle_seconds]
        for k in dead:
            del self._sessions[k]
        return len(dead)

    def _persist(self, key: tuple):
        if self.store:
            self.store.save(self._sessions[key])

    def save_all(self):
        if self.store:
            for session in self._sessions.values():
                self.store.save(session)
