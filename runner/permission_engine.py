"""
Permission & Policy Engine — SHRRI AI OS v2

Real enforcement layer. The context_builder's "restricted tier" note
is a prompt hint the LLM *should* follow — this module is the backstop
that blocks the tool call in code even if the LLM tries anyway.

Usage pattern (once provider_router/tool-calling is wired in):

    engine = PermissionEngine()
    if not engine.is_allowed(session.permission_tier, tool_name):
        return engine.denial_message(tool_name)
    # else: actually run the tool

Tiers:
  "main"        -> full access, all tools
  "restricted"  -> read-only / informational tools only
"""

RESTRICTED_ALLOWED_TOOLS = {
    "weather_tool",
    "math_tool",
    "web_search",
    "calendar_read",   # read-only calendar lookups, not create/delete
}

MAIN_ONLY_TOOLS = {
    "shell_exec",
    "file_write",
    "file_delete",
    "whatsapp_send",
    "telegram_send_other",
    "gmail_send",
    "calendar_write",
}


class PermissionEngine:
    def is_allowed(self, permission_tier: str, tool_name: str) -> bool:
        if permission_tier == "main":
            return True

        if tool_name in MAIN_ONLY_TOOLS:
            return False

        if tool_name in RESTRICTED_ALLOWED_TOOLS:
            return True

        # default-deny: unknown tools are blocked for restricted tier
        return False

    def denial_message(self, tool_name: str) -> str:
        return (
            f"Tool '{tool_name}' requires main-tier access. "
            "This request is coming from an unapproved sender."
        )
