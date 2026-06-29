"""WhatsApp tool — talks to the local wa_bridge (Baileys) sidecar over HTTP
instead of driving a browser. See ~/shrri/wa_bridge/index.js.

The bridge must be running on 127.0.0.1:3001 (or whatever WA_BRIDGE_PORT is
set to) for any of these functions to work. If it's down, every function
below returns a clear "GAP: ..." string rather than hanging or crashing —
same convention the rest of this codebase uses for "couldn't do it" results.
"""
import os
import requests

WA_BRIDGE_URL = os.environ.get("WA_BRIDGE_URL", "http://127.0.0.1:3001")
TIMEOUT = 30  # seconds — generous, since a slow WhatsApp-side response
              # shouldn't make the whole bot hang indefinitely either


def _post(path: str, payload: dict) -> dict:
    """POST to the bridge and return its JSON body. Never raises --
    network/timeout/connection errors are turned into a GAP-style dict
    so callers don't need their own try/except around every call."""
    try:
        resp = requests.post(f"{WA_BRIDGE_URL}{path}", json=payload, timeout=TIMEOUT)
        try:
            return resp.json()
        except ValueError:
            return {"ok": False, "error": f"GAP: bridge returned non-JSON response (status {resp.status_code})"}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "error": "GAP: WhatsApp bridge is not running. Start it with: node ~/shrri/wa_bridge/index.js"}
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "GAP: WhatsApp bridge timed out — it may be reconnecting to WhatsApp."}
    except Exception as e:
        return {"ok": False, "error": f"GAP: bridge request failed — {e}"}


def _result_or_gap(data: dict) -> str:
    """Bridge responses are always {"ok": bool, "result": str} or
    {"ok": false, "error": str}. Collapse that into the single-string
    convention the rest of this codebase expects from tool functions."""
    if data.get("ok"):
        return data.get("result", "Done.")
    return data.get("error", "GAP: unknown bridge error.")


def send_whatsapp_confirmed(contact: str, text: str) -> str:
    """Actually send a message -- called only after the user has confirmed
    via the yes/no pending-action flow in client.py. This is the function
    that talks to the bridge; nothing upstream of the confirmation calls
    this directly.

    Resolution order: Google Contacts first (since that's the richer,
    user-maintained source), then fall back to the bridge's own cached
    name->jid map if Google Contacts doesn't have this person. Either way,
    the bridge only ever sees a phone number or jid, never a name lookup
    failure it has to guess at -- if Google Contacts resolves it, we send
    the digits straight through."""
    target = contact
    try:
        from tools.contacts_sync import lookup_number
        number = lookup_number(contact)
        if number:
            target = number
    except Exception:
        pass  # Google Contacts lookup failing shouldn't block falling back
             # to the bridge's own name resolution below.
    data = _post("/send", {"contact": target, "text": text})
    return _result_or_gap(data)


def reply_to_message(contact: str, reply_text: str) -> str:
    """Quote-reply to the latest message in a chat."""
    data = _post("/reply", {"contact": contact, "text": reply_text})
    return _result_or_gap(data)


def delete_last_message(contact: str) -> str:
    """Delete the last message *you* sent in a chat."""
    data = _post("/delete", {"contact": contact})
    return _result_or_gap(data)


def forward_message(from_contact: str, to_contact: str) -> str:
    """Forward the latest message from one chat to another."""
    data = _post("/forward", {"from_contact": from_contact, "to_contact": to_contact})
    return _result_or_gap(data)


def bridge_health() -> dict:
    """Quick health check -- useful for diagnostics/debugging, not used
    in the normal dispatch flow. Returns the raw /health response, or a
    GAP dict shaped the same way callers of _post already expect."""
    try:
        resp = requests.get(f"{WA_BRIDGE_URL}/health", timeout=5)
        return resp.json()
    except Exception as e:
        return {"ok": False, "error": f"GAP: bridge health check failed — {e}"}
