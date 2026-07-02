"""
Provider Router Adapter — SHRRI AI OS v2

Thin adapter around your existing engine/multi_router.py. Keeps the
Runner decoupled from the exact routing implementation — if the
underlying router changes, only this file needs updating.

Does NOT reimplement routing logic — just calls route() and normalizes
the response shape for Runner._execute_action.

Default capability is "conversation" (matches config/capability_map.py
keys exactly — there is no generic "chat" capability).
"""

import sys
from pathlib import Path

# ensure ~/shrri root is importable (engine/, config/ live there)
SHRRI_ROOT = Path.home() / "shrri"
if str(SHRRI_ROOT) not in sys.path:
    sys.path.insert(0, str(SHRRI_ROOT))

from engine.multi_router import route as _route


class ProviderRouter:
    def __init__(self, default_capability: str = "conversation", verbose: bool = False):
        self.default_capability = default_capability
        self.verbose = verbose

    def generate(self, prompt: str, capability: str | None = None) -> dict:
        cap = capability or self.default_capability
        result = _route(cap, prompt, verbose=self.verbose)

        if result["success"]:
            return {
                "success": True,
                "text": result["response"],
                "provider": result["provider"],
                "model": result["model"],
            }
        return {
            "success": False,
            "text": None,
            "error": result.get("error", "unknown routing failure"),
        }
