"""
Audit Logger — SHRRI AI OS v2

Append-only log of every tool-call decision (allowed or denied) made by
PermissionEngine. Plain JSONL file — simple, greppable, no DB overhead.
This is what lets you actually know if someone tried something risky.
"""

import json
import time
from pathlib import Path

LOG_PATH = Path.home() / ".shrri" / "audit.jsonl"


class AuditLogger:
    def __init__(self, log_path: Path = LOG_PATH):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path = log_path

    def log(self, channel: str, peer_id: str, permission_tier: str,
             tool_name: str, allowed: bool, extra: dict | None = None) -> None:
        entry = {
            "ts": time.time(),
            "channel": channel,
            "peer_id": peer_id,
            "permission_tier": permission_tier,
            "tool": tool_name,
            "allowed": allowed,
            "extra": extra or {},
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def recent_denials(self, limit: int = 20) -> list[dict]:
        if not self.log_path.exists():
            return []
        with open(self.log_path) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        denials = [l for l in lines if not l["allowed"]]
        return denials[-limit:]
