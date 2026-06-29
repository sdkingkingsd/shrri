"""
Send a Telegram message to the owner — used by cron reminders.
Reads BOT_TOKEN and YOUR_ID directly from telegram_bot.py so no duplication.
"""
import sys, os, re
sys.path.insert(0, os.path.expanduser("~/shrri"))

def _load_creds():
    path = os.path.expanduser("~/shrri/telegram_bot.py")
    with open(path) as f:
        content = f.read()
    token = re.search(r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']', content)
    uid = re.search(r'YOUR_ID\s*=\s*(\d+)', content)
    if not token or not uid:
        raise ValueError("BOT_TOKEN or YOUR_ID not found in telegram_bot.py")
    return token.group(1), int(uid.group(1))

def send_reminder(task: str) -> bool:
    """Send a reminder with snooze buttons."""
    try:
        import urllib.request, urllib.parse, json
        token, chat_id = _load_creds()
        # Build inline keyboard with snooze options
        keyboard = {"inline_keyboard": [[
            {"text": "💤 5 min", "callback_data": f"snooze|5|{task}"},
            {"text": "💤 10 min", "callback_data": f"snooze|10|{task}"},
            {"text": "💤 30 min", "callback_data": f"snooze|30|{task}"},
            {"text": "✅ Done", "callback_data": f"snooze|0|{task}"}
        ]]}
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": f"⏰ SHRRI Reminder: {task}",
            "reply_markup": json.dumps(keyboard)
        }).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception as e:
        print(f"[telegram_notify] Error: {e}", file=sys.stderr)
        return False

def send_message(text: str) -> bool:
    """Send a message to the owner via Telegram bot. Returns True on success."""
    try:
        import urllib.request, urllib.parse, json
        token, chat_id = _load_creds()
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception as e:
        print(f"[telegram_notify] Error: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    # Usage: python3 telegram_notify.py "message"
    # Usage: python3 telegram_notify.py --reminder "task"
    if len(sys.argv) >= 3 and sys.argv[1] == "--reminder":
        task = " ".join(sys.argv[2:])
        ok = send_reminder(task)
    else:
        msg = " ".join(sys.argv[1:]) or "Test from SHRRI"
        ok = send_message(msg)
    print("Sent ✅" if ok else "Failed ❌")
