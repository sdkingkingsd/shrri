"""
SHRRI Runner — SHRRI AI OS v2 main execution engine.

Wires together: SessionManager (persistence), ContextBuilder,
PermissionEngine, AuditLogger, PairingManager, and now ProviderRouter —
real LLM calls through your existing multi-provider routing.
"""

from runner.session_manager import SessionManager
from runner.context_builder import ContextBuilder
from runner.permission_engine import PermissionEngine
from runner.persistence import SessionStore
from runner.audit_log import AuditLogger
from runner.pairing import PairingManager
from runner.provider_router import ProviderRouter


class Runner:
    def __init__(self, base_system_prompt: str, main_peer_ids: dict | None = None,
                 use_persistence: bool = True):
        store = SessionStore() if use_persistence else None
        self.sessions = SessionManager(main_peer_ids=main_peer_ids, store=store)
        self.context_builder = ContextBuilder(base_system_prompt)
        self.permissions = PermissionEngine()
        self.audit = AuditLogger()
        self.pairing = PairingManager()
        self.provider_router = ProviderRouter()

    def handle_message(self, channel: str, peer_id: str, message: str) -> str:
        session = self.sessions.get_or_create(channel, peer_id)
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

        context = self.context_builder.build(session, message)
        reply = self._real_model_call(context, message)

        session.add_turn("user", message)
        session.add_turn("assistant", reply)
        return reply

    def _real_model_call(self, context: dict, message: str) -> str:
        # build a single prompt string from the message list context builder made
        full_prompt = "\n".join(
            f"{m['role']}: {m['content']}" for m in context["messages"]
        )
        result = self.provider_router.generate(full_prompt)

        if result["success"]:
            return result["text"]
        return f"[provider error: {result['error']}]"


if __name__ == "__main__":
    runner = Runner(
        base_system_prompt="You are SHRRI, Sd's personal AI assistant. Keep replies short.",
        main_peer_ids={"telegram": "TEST_MAIN_ID"},
        use_persistence=True,
    )

    print("main tier, real model call:")
    print(runner.handle_message("telegram", "TEST_MAIN_ID", "What is 2+2? Answer in one word."))
