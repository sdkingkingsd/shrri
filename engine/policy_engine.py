"""
Policy Engine — SHRRI Phase 13
Evaluates broad access policies beyond basic tool gating.
"""
import json
from pathlib import Path

POLICY_PATH = Path.home() / ".shrri" / "policies.json"

DEFAULT_POLICIES = {
    "allow_web_search": True,
    "allow_code_execution": True,
    "allow_file_write": True,
    "allow_shell_commands": False,
    "allow_external_api_calls": True,
    "max_tokens_per_request": 4096,
    "max_requests_per_minute": 60,
    "blocked_domains": [],
    "allowed_tools": ["*"],
    "denied_tools": []
}


class PolicyEngine:
    def __init__(self):
        POLICY_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not POLICY_PATH.exists():
            POLICY_PATH.write_text(json.dumps(DEFAULT_POLICIES, indent=2))
        with open(POLICY_PATH) as f:
            self._policies = json.load(f)

    def check(self, action: str, context: dict = None) -> tuple[bool, str]:
        """Returns (allowed, reason)."""
        context = context or {}

        # Tool check
        denied = self._policies.get("denied_tools", [])
        if action in denied:
            return False, f"Tool '{action}' is in denied_tools policy"

        allowed_tools = self._policies.get("allowed_tools", ["*"])
        if "*" not in allowed_tools and action not in allowed_tools:
            return False, f"Tool '{action}' not in allowed_tools policy"

        # Specific action checks
        if action == "web_search" and not self._policies.get("allow_web_search", True):
            return False, "Web search disabled by policy"
        if action == "shell" and not self._policies.get("allow_shell_commands", False):
            return False, "Shell commands disabled by policy"
        if action == "file_write" and not self._policies.get("allow_file_write", True):
            return False, "File writes disabled by policy"
        if action == "code_exec" and not self._policies.get("allow_code_execution", True):
            return False, "Code execution disabled by policy"

        # Domain check
        if action == "web_fetch":
            domain = context.get("domain", "")
            blocked = self._policies.get("blocked_domains", [])
            if any(b in domain for b in blocked):
                return False, f"Domain '{domain}' blocked by policy"

        return True, "allowed"

    def get(self, key: str):
        return self._policies.get(key)

    def set(self, key: str, value):
        self._policies[key] = value
        POLICY_PATH.write_text(json.dumps(self._policies, indent=2))

    def summary(self) -> dict:
        return dict(self._policies)
