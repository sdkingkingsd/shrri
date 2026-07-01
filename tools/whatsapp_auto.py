import os, sys, json, threading, re
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.expanduser("~/shrri"))

BRIDGE_URL = "http://127.0.0.1:3001"
AUTO_FLAG  = "whatsapp_auto_mode"
QUIET_SECS = 600

URGENT_KEYWORDS = [
    "emergency", "urgent", "accident", "hospital", "help me",
    "please call", "call me", "dying", "hurt", "danger", "asap",
    "immediately", "critical", "serious"
]

_convos = {}
_lock   = threading.Lock()

def _get_memory():
    from engine.memory import Memory
    return Memory()

def _router():
    from engine.router import Router
    return Router()

FLAG_FILE = os.path.expanduser("~/.shrri/wa_auto_mode.flag")

def auto_mode_on():
    try:
        return open(FLAG_FILE).read().strip() == "true"
    except Exception:
        return False

def set_auto_mode(enabled):
    os.makedirs(os.path.dirname(FLAG_FILE), exist_ok=True)
    open(FLAG_FILE, 'w').write("true" if enabled else "false")
    # Also save to memory for persistence across reboots
    try:
        _get_memory().save_fact(AUTO_FLAG, "true" if enabled else "false")
    except Exception:
        pass
    if not enabled:
        try:
            import urllib.request
            urllib.request.urlopen("http://127.0.0.1:3002/disable", timeout=3)
        except Exception:
            pass
    if not enabled:
        # Cancel all active conversation timers immediately.
        with _lock:
            for state in _convos.values():
                if state.get("timer"):
                    state["timer"].cancel()
            _convos.clear()

def _send_whatsapp(jid, text):
    import urllib.request
    body = json.dumps({"contact": jid, "text": text}).encode()
    req  = urllib.request.Request(
        BRIDGE_URL + "/send", data=body,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def _get_telegram_creds():
    src = open(os.path.expanduser("~/shrri/telegram_bot.py")).read()
    tm = re.search(r'BOT_TOKEN\s*=\s*"([^"]+)"', src)
    if not tm:
        tm = re.search(r"BOT_TOKEN\s*=\s*'([^']+)'", src)
    cm = re.search(r'YOUR_ID\s*=\s*(\d+)', src)
    if tm and cm:
        return tm.group(1), cm.group(1)
    return None, None

def _send_telegram(text):
    try:
        import urllib.request, urllib.parse
        token, chat_id = _get_telegram_creds()
        if not token or not chat_id:
            print("[auto] Telegram credentials not found")
            return
        params = urllib.parse.urlencode(
            {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        )
        url = "https://api.telegram.org/bot" + token + "/sendMessage?" + params
        urllib.request.urlopen(url, timeout=10)
    except Exception as e:
        print(f"[auto] Telegram alert failed: {e}")

def _is_urgent(text, history):
    txt = text.lower()
    if any(k in txt for k in URGENT_KEYWORDS):
        return True
    try:
        r = _router()
        conv = "\n".join(f"{h['role']}: {h['content']}" for h in history[-6:])
        prompt = (
            f"Conversation:\n{conv}\n\nLatest: \"{text}\"\n\n"
            "Is this urgent and needs Shrridharshan's immediate attention? Reply YES or NO only."
        )
        return r.chat(prompt, task="fast", web_search=False).strip().upper().startswith("YES")
    except Exception:
        return False

def _generate_reply(name, text, history):
    try:
        r = _router()
        conv = "\n".join(f"{h['role']}: {h['content']}" for h in history[-10:])
        prompt = (
            f"You are Shrridharshan (called 'da' by friends), a 21-year-old CS student from Erode, Tamil Nadu. "
            f"You are chatting on WhatsApp with {name}. NEVER reveal you are an AI.\n\n"
            f"YOUR PERSONALITY:\n"
            f"- Casual, funny, friendly with close friends\n"
            f"- Use Tanglish naturally (mix Tamil words like da, bro, machan, dei, po, vaa, enna, seri, ok da, illa, oru, romba, super, epdi, inge, athan)\n"
            f"- Keep replies SHORT — 1 to 2 sentences max like real WhatsApp chat\n"
            f"- No long paragraphs, no formal language with friends\n"
            f"- Use emojis sparingly like 😂 💀 🔥 only when it fits\n"
            f"- Never say 'I understand' or 'That\'s great' — those sound like AI\n"
            f"- If you don\'t know something just say 'theriyala da' or 'no idea bro'\n"
            f"- Match the vibe: if they\'re joking, joke back; if serious, be brief and direct\n\n"
            f"MIRROR THEIR STYLE:\n"
            f"- Tanglish message → reply in Tanglish\n"
            f"- Pure English → casual English\n"
            f"- Pure Tamil → Tanglish\n"
            f"- Short message → short reply\n"
            f"- Emoji heavy → use 1-2 emojis\n\n"
            f"Conversation so far:\n{conv}\n\n"
            f"{name}: {text}\n"
            f"Shrridharshan (reply as him, 1-2 sentences only, no labels):"
        )
        reply = r.chat(prompt, task="fast", web_search=False).strip()
        reply = re.sub(r"^Shrridharshan:\s*", "", reply)
        # Drop any leaked reasoning lines
        lines = [l for l in reply.splitlines()
                 if not l.startswith(name + " sent") and not l.startswith("Shrridharshan:")]
        return " ".join(lines).strip()
    except Exception as e:
        print(f"[auto] Reply generation failed: {e}")
        return ""

def _send_summary(jid, name, history):
    if not history:
        return
    try:
        r = _router()
        conv = "\n".join(f"{h['role']}: {h['content']}" for h in history)
        prompt = (
            f"Summarise this WhatsApp conversation between Shrridharshan (auto-replied by SHRRI) "
            f"and {name} in 2-3 sentences. Note if anything needs follow-up.\n\n{conv}"
        )
        summary = r.chat(prompt, task="fast", web_search=False).strip()
        _send_telegram(
            f"📱 <b>Auto-chat summary — {name}</b>\n\n{summary}\n\n"
            f"<i>({len(history)} messages exchanged while you were away)</i>"
        )
    except Exception as e:
        print(f"[auto] Summary failed: {e}")

def _handle_incoming(jid, name, text):
    if not auto_mode_on():
        return
    with _lock:
        if jid not in _convos:
            _convos[jid] = {"history": [], "timer": None}
        state = _convos[jid]
        if state["timer"]:
            state["timer"].cancel()
        state["history"].append({"role": name, "content": text})

    if _is_urgent(text, state["history"]):
        _send_telegram(
            f"🚨 <b>Urgent message from {name}!</b>\n\n\"{text}\"\n\n"
            f"<i>SHRRI is auto-replying but you may want to step in.</i>"
        )

    reply = _generate_reply(name, text, state["history"])
    if reply:
        try:
            _send_whatsapp(jid, reply)
            with _lock:
                state["history"].append({"role": "Shrridharshan", "content": reply})
        except Exception as e:
            print(f"[auto] Send failed: {e}")

    def on_quiet():
        if not auto_mode_on():
            return
        with _lock:
            h = list(state["history"])
            _convos.pop(jid, None)
        _send_summary(jid, name, h)

    with _lock:
        t = threading.Timer(QUIET_SECS, on_quiet)
        t.daemon = True
        t.start()
        state["timer"] = t

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        if self.path == "/incoming":
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length))
            threading.Thread(
                target=_handle_incoming,
                args=(body["jid"], body["name"], body["text"]),
                daemon=True
            ).start()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        elif self.path == "/disable":
            with _lock:
                for state in _convos.values():
                    if state.get("timer"):
                        state["timer"].cancel()
                _convos.clear()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return

if __name__ == "__main__":
    print("[auto] SHRRI WhatsApp auto-reply server listening on port 3002")
    HTTPServer(("127.0.0.1", 3002), Handler).serve_forever()
