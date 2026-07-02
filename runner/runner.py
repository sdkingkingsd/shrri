"""
SHRRI Runner — SHRRI AI OS v2 main execution engine.

Wires together: SessionManager (with persistence), ContextBuilder,
PermissionEngine, AuditLogger, and PairingManager.

New commands handled directly by the runner (not the LLM):
  "pair"                 -> restricted sender requests a pairing code
  "approve <code>"       -> main-tier sender approves a pending code
"""

from runner.session_manager import SessionManager
from runner.context_builder import ContextBuilder
from runner.permission_engine import PermissionEngine
from runner.persistence import SessionStore
from runner.audit_log import AuditLogger
from runner.pairing import PairingManager


class Runner:
    def __init__(self, base_system_prompt: str, main_peer_ids: dict | None = None,
                 use_persistence: bool = True):
        store = SessionStore() if use_persistence else None
        self.sessions = SessionManager(main_peer_ids=main_peer_ids, store=store)
        self.context_builder = ContextBuilder(base_system_prompt)
        self.permissions = PermissionEngine()
        self.audit = AuditLogger()
        self.pairing = PairingManager()

    def handle_message(self, channel: str, peer_id: str, message: str) -> str:
        session = self.sessions.get_or_create(channel, peer_id)

        # --- pairing commands intercepted before normal flow ---
        stripped = message.strip().lower()

        if stripped == "pair":
            code = self.pairing.request_code(channel, peer_id)
            reply = f"Pairing code: {code}. Ask the owner to send 'approve {code}'."
            session.add_turn("user", message)
            session.add_turn("assistant", reply)
            return reply

        if stripped.startswith("approve "):
            if session.permission_tier != "main":
                reply = "Only main-tier users can approve pairing requests."
                session.add_turn("user", message)
                session.add_turn("assistant", reply)
                self.audit.log(channel, peer_id, session.permission_tier,
                                "pairing_approve", allowed=False)
                return reply

            code = stripped.split("approve ", 1)[1].strip()
            info = self.pairing.approve(code)
            if not info:
                reply = f"Code {code} is invalid or expired."
            else:
                self.sessions.upgrade_to_main(info["channel"], info["peer_id"])
                reply = f"Approved {info['peer_id']} on {info['channel']} to main tier."
                self.audit.log(channel, peer_id, session.permission_tier,
                                "pairing_approve", allowed=True,
                                extra={"approved_peer": info["peer_id"]})
            session.add_turn("user", message)
            session.add_turn("assistant", reply)
            return reply
        # ---------------------------------------------------------

        context = self.context_builder.build(session, message)

        # --- STUB: replace with real provider_router call ---
        model_action = self._stub_model_action(message)
        reply = self._execute_action(model_action, session, channel, peer_id)
        # ------------------------------------------------------

        session.add_turn("user", message)
        session.add_turn("assistant", reply)
        return reply

    def _stub_model_action(self, message: str) -> dict:
        if "run shell" in message.lower():
            return {"type": "tool_call", "tool": "shell_exec", "args": {"cmd": message}}
        return {"type": "text", "content": f"echo: {message}"}

    def _execute_action(self, action: dict, session, channel: str, peer_id: str) -> str:
        if action["type"] == "text":
            return action["content"]

        if action["type"] == "tool_call":
            tool_name = action["tool"]
            allowed = self.permissions.is_allowed(session.permission_tier, tool_name)
            self.audit.log(channel, peer_id, session.permission_tier, tool_name, allowed)
            if not allowed:
                return self.permissions.denial_message(tool_name)
            return f"[would execute tool: {tool_name}]"

        return "Unrecognized action type."


if __name__ == "__main__":
    runner = Runner(
        base_system_prompt="You are SHRRI, Sd's personal AI assistant.",
        main_peer_ids={"telegram": "TEST_MAIN_ID"},
        use_persistence=True,
    )

    print("restricted sender requests pairing:")
    reply = runner.handle_message("telegram", "STRANGER_1", "pair")
    print(reply)
    code = reply.split("Pairing code: ")[1].split(".")[0]

    print("\nmain tier approves the code:")
    print(runner.handle_message("telegram", "TEST_MAIN_ID", f"approve {code}"))

    print("\nformerly-restricted sender now runs a tool:")
    print(runner.handle_message("telegram", "STRANGER_1", "run shell whoami"))

    print("\naudit log recent denials:")
    print(runner.audit.recent_denials())
