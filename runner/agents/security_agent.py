"""
Security Agent — SHRRI AI OS v2 (Phase 5)

Thin wrapper around existing security infrastructure:
  - runner.permission_engine.PermissionEngine (tier-based tool access rules)
  - runner.audit_log.AuditLogger (real append-only log of allow/deny decisions)
  - tools.doctor.run_doctor (system/provider health check — the closest
    thing to a general security/status report already in the codebase)

No new enforcement logic here — this agent only reports on and
explains decisions the real enforcement layer already makes.

Intent routing (checked in order):
  - "denial"/"denied"/"suspicious"/"blocked" -> recent denials from audit log
  - "allowed"/"can I"/"is X allowed"         -> explain PermissionEngine rules
  - "health"/"status"/"check" (system-wide)  -> run doctor.run_doctor()
  - everything else                          -> summarize security posture
    (tiers, restricted tools, main-only tools) from PermissionEngine directly
"""

import io
import re
import contextlib

from runner.permission_engine import PermissionEngine, RESTRICTED_ALLOWED_TOOLS, MAIN_ONLY_TOOLS
from runner.audit_log import AuditLogger


class SecurityAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._engine = PermissionEngine()
        self._audit = AuditLogger()

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "").strip()
        low = prompt.lower()
        if self.verbose:
            print(f"[security_agent] Handling: {prompt[:80]!r}")

        wants_denials = bool(re.search(r"\b(denial|denied|suspicious|blocked|unauthorized)\b", low))
        wants_restricted = bool(re.search(r"\brestrict", low))

        # If BOTH denials and restricted-tools info are asked for, combine them
        # instead of only answering the first thing the regex happens to match.
        if wants_denials and wants_restricted:
            denials = self._audit.recent_denials(limit=20)
            denial_str = (
                "No denied tool-call attempts logged — nothing suspicious found."
                if not denials else
                "⚠️ Recent denied tool-call attempts:\n" + "\n".join(
                    f"- {d['channel']}/{d['peer_id']} tried '{d['tool']}' (tier: {d['permission_tier']})"
                    for d in denials
                )
            )
            restricted_list = ", ".join(sorted(RESTRICTED_ALLOWED_TOOLS)) or "(none)"
            return f"Restricted-tier allowed tools: {restricted_list}\n\n{denial_str}"

        # Recent denials / suspicious activity only
        if wants_denials:
            denials = self._audit.recent_denials(limit=20)
            if not denials:
                return "No denied tool-call attempts logged — nothing suspicious found."
            lines = [
                f"- {d['channel']}/{d['peer_id']} tried '{d['tool']}' "
                f"(tier: {d['permission_tier']})"
                for d in denials
            ]
            return "⚠️ Recent denied tool-call attempts:\n" + "\n".join(lines)

        # "is X allowed" / "can I use X"
        allowed_match = re.search(r"\b(?:is|can i use|allowed to use)\s+([a-z_]+)\b.*\ballow", low) \
            or re.search(r"\bcan i use\s+([a-z_]+)", low) \
            or re.search(r"\bis\s+([a-z_]+)\s+allowed", low)
        if allowed_match:
            tool_name = allowed_match.group(1)
            main_ok = self._engine.is_allowed("main", tool_name)
            restricted_ok = self._engine.is_allowed("restricted", tool_name)
            return (
                f"Tool '{tool_name}': allowed on main tier = {main_ok}, "
                f"allowed on restricted tier = {restricted_ok}."
            )

        # System health / status check
        if re.search(r"\b(health|status|diagnost|doctor)\b", low) or "check" in low:
            from tools.doctor import run_doctor
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                run_doctor()
            return buf.getvalue()

        # Default: summarize security posture
        restricted_list = ", ".join(sorted(RESTRICTED_ALLOWED_TOOLS)) or "(none)"
        main_only_list = ", ".join(sorted(MAIN_ONLY_TOOLS)) or "(none)"
        recent = self._audit.recent_denials(limit=5)
        recent_str = f"{len(recent)} denial(s) in recent log" if recent else "no recent denials"
        return (
            "🔒 Security posture:\n"
            f"- Restricted-tier allowed tools: {restricted_list}\n"
            f"- Main-tier-only tools: {main_only_list}\n"
            f"- Unknown tools are default-denied for restricted tier\n"
            f"- Audit log: {recent_str}"
        )
