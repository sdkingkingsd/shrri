"""
DM Pairing — SHRRI AI OS v2

Lets an unknown/restricted sender request approval instead of being
permanently stuck at restricted tier. Flow:

  1. Unknown sender sends any message -> gets a pairing code back,
     request is logged as pending.
  2. You (main tier) send: "approve <code>" from your own session ->
     that peer_id gets upgraded to main tier.
  3. Codes expire after PAIRING_TTL_SECONDS if unused.

This does NOT auto-upgrade anyone. Approval must come from a main-tier
sender explicitly. Keeps the security model intact.
"""

import random
import string
import time

PAIRING_TTL_SECONDS = 600  # 10 minutes


class PairingManager:
    def __init__(self):
        # code -> {channel, peer_id, created_at}
        self._pending: dict[str, dict] = {}

    def request_code(self, channel: str, peer_id: str) -> str:
        self._expire_old()
        # reuse existing code if this peer already has a pending request
        for code, info in self._pending.items():
            if info["channel"] == channel and info["peer_id"] == peer_id:
                return code

        code = "".join(random.choices(string.digits, k=6))
        self._pending[code] = {
            "channel": channel,
            "peer_id": peer_id,
            "created_at": time.time(),
        }
        return code

    def approve(self, code: str) -> dict | None:
        self._expire_old()
        info = self._pending.pop(code, None)
        return info  # None if invalid/expired, else {"channel", "peer_id", "created_at"}

    def _expire_old(self) -> None:
        now = time.time()
        expired = [c for c, i in self._pending.items()
                   if now - i["created_at"] > PAIRING_TTL_SECONDS]
        for c in expired:
            del self._pending[c]
