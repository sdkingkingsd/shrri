import re


# These tools are hardcoded — faster and more reliable than LLM for exact matches
def _hardcoded_intent(message: str):
    msg = message.lower()

    # Math
    if re.search(r"\d+\s*(?:[\+\-\*/%\^]|times|multiplied by|plus|minus|divided by)\s*\d+", msg):
        return {"tool": "math", "action": "calculate", "params": {"query": message}}
    if re.search(r"[0-9]+\s*%\s*of\s*[0-9]+", msg):
        return {"tool": "math", "action": "calculate", "params": {"query": message}}

    # Time/Date
    if any(t in msg for t in ["what date", "today's date", "what day is it", "current date", "which date"]):
        return {"tool": "date", "action": "get_date", "params": {}}
    if any(t in msg for t in ["what time", "current time", "time now", "what's the time", "tell me the time"]):
        return {"tool": "time", "action": "get_time", "params": {}}

    # Python code execution
    if "```python" in message:
        return {"tool": "pyexec", "action": "run", "params": {"query": message}}

    # YouTube
    if "youtube.com" in msg or "youtu.be" in msg:
        return {"tool": "youtube", "action": "summarize", "params": {"query": message}}

    # Draft detection — must come before send check
    if re.search(r"[^\s]+@[^\s]+\.[^\s]+", msg) and any(t in msg for t in ["draft", "save draft", "save a draft"]):
        to = re.search(r"to ([^\s]+@[^\s]+)", message, re.IGNORECASE)
        subject = re.search(r"subject (.+?) body", message, re.IGNORECASE)
        body = re.search(r"body (.+)$", message, re.IGNORECASE | re.DOTALL)
        return {"tool": "gmail", "action": "draft", "params": {
            "to": to.group(1) if to else "",
            "subject": subject.group(1).strip() if subject else "Draft",
            "body": body.group(1).strip() if body else message
        }}
    # Email address present = likely gmail send
    if re.search(r"[^\s]+@[^\s]+\.[^\s]+", msg) and any(t in msg for t in ["send", "mail", "email", "write", "compose"]):
        to = re.search(r"to ([^\s]+@[^\s]+)", message, re.IGNORECASE)
        subject = re.search(r"subject (.+?) body", message, re.IGNORECASE)
        body = re.search(r"body (.+)$", message, re.IGNORECASE | re.DOTALL)
        return {"tool": "gmail", "action": "send", "params": {
            "to": to.group(1) if to else "",
            "subject": subject.group(1).strip() if subject else "Message from SHRRI",
            "body": body.group(1).strip() if body else message
        }}

    # WhatsApp send — must fire before LLM, since the classifier can
    # occasionally confuse "send X to Y" with whatsapp_read (we hit this
    # in testing: "send hi to Naghul Vit" got misclassified as a read).
    # Only matches when there's no @ (to avoid stealing email-send intents)
    # and the message doesn't look like a read/check request.
    if not re.search(r"[^\s]+@[^\s]+\.[^\s]+", msg):
        _wa_send_pat = re.search(
            r"\bsend\b.+\bto\b\s+([a-zA-Z][a-zA-Z\s]{1,30})", msg)
        _wa_read_words = ["check", "read", "any message", "any messages", "what did", "show me"]
        if _wa_send_pat and "whatsapp" not in msg.replace("send", "") or (
            _wa_send_pat and not any(w in msg for w in _wa_read_words)
        ):
            if not any(w in msg for w in _wa_read_words) and "email" not in msg and "mail" not in msg:
                return {"tool": "whatsapp", "action": "send", "params": {"query": message}}

    # WhatsApp send — must fire before LLM, since the classifier can
    # occasionally confuse "send X to Y" with whatsapp_read (hit this in
    # testing: "send hi to Naghul Vit" got misclassified as a read).
    if not re.search(r"[^\s]+@[^\s]+\.[^\s]+", msg):
        _wa_read_words = ["check", "read", "any message", "any messages", "what did", "show me"]
        if not any(w in msg for w in _wa_read_words):
            if re.search(r"\bsend\b", msg) and re.search(r"\bsend\b.{0,40}\bto\b\s+[a-zA-Z0-9]", msg):
                return {"tool": "whatsapp", "action": "send", "params": {"query": message}}
            # "message <name> <text>" -- e.g. "message dharini i love you"
            _msg_pat = re.search(r"^message\s+([a-zA-Z][a-zA-Z]{1,20})\s+(.+)$", msg)
            if _msg_pat:
                return {"tool": "whatsapp", "action": "send", "params": {"query": message}}

    # Web extract — read a URL
    import re as _re
    _url_match = _re.search(r'https?://\S+', message)
    if _url_match and any(w in msg for w in ["read","extract","summarise","summarize","open","fetch","get content","what does"]):
        return {"tool": "web_extract", "action": "extract", "params": {"url": _url_match.group()}}

    # browser — screenshot / click
    _url2 = re.search(r"https?://\S+", msg)
    if _url2 and any(w in msg for w in ["screenshot", "click", "type into", "fill in"]):
        if "screenshot" in msg:
            return {"tool": "browser", "action": "screenshot", "params": {"url": _url2.group()}}
        if "click" in msg:
            return {"tool": "browser", "action": "click", "params": {"url": _url2.group(), "selector": "button"}}

    # WhatsApp auto-mode toggle
    if re.search(r"\b(enable|turn on|activate)\b.*\bauto.?(mode|reply|chat)\b", msg) or \
       re.search(r"\bauto.?(mode|reply|chat)\b.*\b(on|enable)\b", msg):
        return {"tool": "wa_auto", "action": "enable", "params": {}}
    if re.search(r"\b(disable|turn off|deactivate|stop)\b.*\bauto.?(mode|reply|chat)\b", msg) or \
       re.search(r"\bauto.?(mode|reply|chat)\b.*\b(off|disable)\b", msg):
        return {"tool": "wa_auto", "action": "disable", "params": {}}

    # Recurring reminder — must fire before LLM to avoid calendar misrouting
    _remind_triggers = ["remind me every", "every monday", "every tuesday", "every wednesday",
        "every thursday", "every friday", "every saturday", "every sunday",
        "every week", "weekly remind", "every day", "daily remind", "every morning", "every night"]
    if any(t in msg for t in _remind_triggers) and any(w in msg for w in ["remind", "to ", "notify", "alert"]):
        return {"tool": "reminder", "action": "set", "params": {"query": message}}
    return None


def _llm_detect_intent(message: str) -> dict:
    """Use LLM to understand message intent — no keyword lists needed."""
    from engine.router import Router
    router = Router()

    prompt = f"""You are an intent classifier for SHRRI, a personal AI assistant.
Shrridharshan speaks Tamil, Tanglish, and English. Understand all three.
Tamil hints: "podu" = send/do, "pesinom" = we talked, "pathi" = about, "ku" = to, "check panu" = check, "paru" = look/check.
IMPORTANT RULES:
- Single words like "dei", "da", "yes", "yeah", "ok", "sure" = always "chat"
- Follow-up messages like "summarise it", "explain it", "read it" = "chat" (continuing previous topic)
- "share me", "show me" after a previous tool result = "chat"
- Only classify as a tool if the message CLEARLY and SPECIFICALLY requests that tool's action
Classify this message into exactly ONE of these tools:

Tools available:
- gmail_read: read/check emails or inbox
- gmail_search: search for specific email
- gmail_read_body: open/explain/read full content of a specific email
- gmail_send: send an email (only if explicitly asked to send/write email)
- whatsapp_send: send a whatsapp message to someone
- whatsapp_read: read/check whatsapp messages
- whatsapp_reply: reply to the latest whatsapp message from someone
- whatsapp_delete: delete/unsend the last whatsapp message sent to someone
- whatsapp_forward: forward a whatsapp message from one contact to another
- weather: get weather information
- calendar_today: check today's schedule/events
- calendar_date: check schedule for a specific day (tomorrow, a weekday name, or a specific date)
- calendar_upcoming: check upcoming/this week's events
- calendar_create: create/add a new event or meeting
- calendar_delete: delete/cancel/remove an event
- calendar_update: update/edit/change/reschedule an event
- calendar_search: search/find events by keyword
- calendar_recurring: create a recurring/repeating event (daily/weekly/monthly)
- reminder_set: set a reminder or alert
- reminder_list: show existing reminders
- reminder_delete: delete all reminders or clear all reminders
- reminder_delete_one: delete a specific reminder by keyword
- notes_save: save/add/remember a note
- notes_show: show/list/find notes
- notes_delete: delete a note
- briefing: morning/daily briefing or summary
- news: get latest news or current events
- files: find/search/open files on computer
- system: system controls like shutdown, lock screen
- schedule_add: schedule an automated recurring task
- gmail_reply: reply to an email (e.g. "reply to that email", "reply to John")
- gmail_archive: archive or dismiss an email
- gmail_delete: delete or trash an email
- gmail_mark_read: mark email as read
- gmail_draft: save a draft email
- gmail_attachment: download attachments from an email
- convsearch: search past conversations with SHRRI (user asking about previous chats, what was said before, past discussions)
- memory_search: search SHRRI's semantic memory for facts, topics, or things said (e.g. "do you remember when", "what did i say about", "find in memory", "search memory for")
- chat: general conversation, questions, explanations, help — anything else

Message: "{message}"

Reply with ONLY the tool name, nothing else. No explanation."""

    try:
        result = router.chat(prompt, task="fast", web_search=False)
        tool = result.strip().lower().split()[0].rstrip(".,:")
        return tool
    except Exception:
        return "chat"


def detect_intent(message: str) -> dict:
    # Try hardcoded first (instant, no API call)
    hardcoded = _hardcoded_intent(message)
    if hardcoded:
        return hardcoded

    # Use LLM to understand intent
    tool = _llm_detect_intent(message)

    msg = message.lower()

    if tool == "gmail_read":
        return {"tool": "gmail", "action": "read", "params": {"max_results": 5}}
    elif tool == "gmail_search":
        return {"tool": "gmail", "action": "search", "params": {"query": message}}
    elif tool == "gmail_read_body":
        return {"tool": "gmail", "action": "read_body", "params": {"query": message}}
    elif tool == "gmail_send":
        return {"tool": "gmail", "action": "send", "params": {"query": message}}
    elif tool == "whatsapp_send":
        return {"tool": "whatsapp", "action": "send", "params": {"query": message}}
    elif tool == "whatsapp_read":
        return {"tool": "wa_read", "action": "read", "params": {"query": message}}
    elif tool == "whatsapp_reply":
        return {"tool": "whatsapp", "action": "reply", "params": {"query": message}}
    elif tool == "whatsapp_delete":
        return {"tool": "whatsapp", "action": "delete", "params": {"query": message}}
    elif tool == "whatsapp_forward":
        return {"tool": "whatsapp", "action": "forward", "params": {"query": message}}
    elif tool == "weather":
        return {"tool": "weather", "action": "get", "params": {"query": message}}
    elif tool == "calendar_today":
        return {"tool": "calendar", "action": "today", "params": {}}
    elif tool == "calendar_date":
        return {"tool": "calendar", "action": "date", "params": {"query": message}}
    elif tool == "calendar_upcoming":
        return {"tool": "calendar", "action": "upcoming", "params": {"days": 7}}
    elif tool == "calendar_create":
        return {"tool": "calendar", "action": "create", "params": {"query": message}}
    elif tool == "calendar_delete":
        return {"tool": "calendar", "action": "delete", "params": {"query": message}}
    elif tool == "calendar_update":
        return {"tool": "calendar", "action": "update", "params": {"query": message}}
    elif tool == "calendar_search":
        return {"tool": "calendar", "action": "search", "params": {"query": message}}
    elif tool == "calendar_recurring":
        return {"tool": "calendar", "action": "recurring", "params": {"query": message}}
    elif tool == "reminder_set":
        return {"tool": "reminder", "action": "set", "params": {"query": message}}
    elif tool == "reminder_list":
        return {"tool": "reminder", "action": "list", "params": {}}
    elif tool == "reminder_delete":
        return {"tool": "reminder", "action": "delete_all", "params": {}}
    elif tool == "reminder_delete_one":
        return {"tool": "reminder", "action": "delete_one", "params": {"query": message}}
    elif tool == "notes_save":
        return {"tool": "notes", "action": "save", "params": {"query": message}}
    elif tool == "notes_show":
        return {"tool": "notes", "action": "show", "params": {"query": message}}
    elif tool == "notes_delete":
        return {"tool": "notes", "action": "delete", "params": {"query": message}}
    elif tool == "briefing":
        return {"tool": "briefing", "action": "get", "params": {}}
    elif tool == "news":
        from tools.search import search
        return {"tool": "search", "action": "news", "result": search(message)}
    elif tool == "files":
        return {"tool": "files", "action": "search", "params": {"query": message}}
    elif tool == "system":
        return {"tool": "system", "action": "control", "params": {"query": message}}
    elif tool == "schedule_add":
        from tools.scheduler import add_schedule
        result = add_schedule(message)
        return {"tool": "schedule", "action": "add", "params": {}, "result": result}
    elif tool == "gmail_reply":
        return {"tool": "gmail", "action": "reply", "params": {"query": message}}
    elif tool == "gmail_archive":
        return {"tool": "gmail", "action": "archive", "params": {"query": message}}
    elif tool == "gmail_delete":
        return {"tool": "gmail", "action": "delete", "params": {"query": message}}
    elif tool == "gmail_mark_read":
        return {"tool": "gmail", "action": "mark_read", "params": {"query": message}}
    elif tool == "gmail_draft":
        return {"tool": "gmail", "action": "draft", "params": {"query": message}}
    elif tool == "gmail_attachment":
        return {"tool": "gmail", "action": "attachment", "params": {"query": message}}
    elif tool == "memory_search":
        return {"tool": "memory_search", "action": "search", "params": {"query": message}}
    elif tool == "convsearch":
        from tools.conversation_log import search_conversations, get_recent
        if any(w in msg for w in ["yesterday", "today", "recent", "last"]):
            return {"tool": "convsearch", "result": get_recent(1)}
        return {"tool": "convsearch", "result": search_conversations(message)}
    elif tool == "youtube":
        return {"tool": "youtube", "action": "summarize", "params": {"query": message}}
    else:
        return {"tool": "none", "action": None, "params": {}}


def run_tool(intent: dict, message: str) -> str:
    tool = intent["tool"]
    action = intent["action"]
    params = intent["params"]

    if tool == "whatsapp":
        action = intent.get("action", "send")
        if action == "reply":
            from tools.whatsapp_tool import reply_to_message
            import json, re as _re
            from engine.router import Router as _R; _r = _R()
            _q = params.get("query", message)
            _p = f"""Extract from: "{_q}"
Reply ONLY as JSON: {{"contact": "name of person", "reply_text": "the reply message"}}"""
            try:
                _raw = _re.sub(r"```json|```", "", _r.chat(_p, task="fast", web_search=False)).strip()
                _d = json.loads(_raw)
                return reply_to_message(_d.get("contact",""), _d.get("reply_text",""))
            except Exception as e:
                return f"GAP: could not parse reply request — {e}"
        if action == "delete":
            from tools.whatsapp_tool import delete_last_message
            import re as _re
            _q = params.get("query", message)
            _kw = _re.sub(r'^(delete|unsend|remove)\s+(my\s+)?(last\s+)?(message|whatsapp)?\s*(to|from|sent to)?\s*', '', _q, flags=_re.IGNORECASE).strip()
            return delete_last_message(_kw or _q)
        if action == "forward":
            from tools.whatsapp_tool import forward_message
            import json, re as _re
            from engine.router import Router as _R; _r = _R()
            _q = params.get("query", message)
            _p = f"""Extract from: "{_q}"
Reply ONLY as JSON: {{"from_contact": "source contact name", "to_contact": "destination contact name"}}"""
            try:
                _raw = _re.sub(r"```json|```", "", _r.chat(_p, task="fast", web_search=False)).strip()
                _d = json.loads(_raw)
                return forward_message(_d.get("from_contact",""), _d.get("to_contact",""))
            except Exception as e:
                return f"GAP: could not parse forward request — {e}"
        # Default action is "send" -- extract contact/text the same way
        # reply/forward do above, then hand back a confirmation sentinel
        # instead of sending immediately. client.py owns the actual
        # pending-action state (it has access to self.memory; this
        # function doesn't), so the real send happens there after the
        # user confirms.
        import json, re as _re
        from engine.router import Router as _R; _r = _R()
        _q = params.get("query", message)
        _p = f"""Extract the recipient name and message text from this WhatsApp send request.

Examples:
- "send hi to Naghul" -> {{"contact": "Naghul", "text": "hi"}}
- "send love you to dharini" -> {{"contact": "dharini", "text": "love you"}}
- "message Arun how are you" -> {{"contact": "Arun", "text": "how are you"}}
- "tell Priya happy birthday" -> {{"contact": "Priya", "text": "happy birthday"}}

Now extract from: "{_q}"
Reply ONLY as JSON: {{"contact": "name of person", "text": "the message to send"}}"""
        try:
            _raw = _re.sub(r"```json|```", "", _r.chat(_p, task="fast", web_search=False)).strip()
            _d = json.loads(_raw)
            _contact = _d.get("contact", "")
            _text = _d.get("text", "")
            if not _contact or not _text:
                return "GAP: could not figure out who to send to or what to say."
            return "WHATSAPP_CONFIRM_NEEDED|" + _contact + "|" + _text
        except Exception as e:
            return f"GAP: could not parse send request — {e}"

    if tool == "wa_auto":
        from tools.whatsapp_auto import set_auto_mode
        if action == "enable":
            set_auto_mode(True)
            return "Auto-chat mode enabled. I'll reply to incoming WhatsApp messages as you and alert you if anything's urgent."
        else:
            set_auto_mode(False)
            return "Auto-chat mode disabled. Incoming messages will queue up as normal."

    if tool == "web_extract":
        url = params.get("url") or params.get("query", "")
        if not url.startswith("http"):
            return "GAP: please provide a valid URL to extract."
        from tools.search import web_extract
        content = web_extract(url)
        if content.startswith("Extract failed"):
            return content
        # Summarise the extracted content instead of dumping raw text
        from engine.router import Router as _R
        _r = _R()
        summary = _r.chat("Summarise this web page content clearly and concisely: " + content[:2000], task="fast", web_search=False)
        return summary
    if tool == "browse_agent":
        from tools.browser_agent import browse_agent
        return browse_agent(message)

    if tool == "browser":
        from tools.browser import browser_action
        action = intent.get("action", params.get("action", "open"))
        url = params.get("url", "")
        if not url:
            return "GAP: no URL for browser action."
        selector = params.get("selector", "")
        text = params.get("text", "")
        submit = params.get("submit", False)
        path = params.get("path", "/tmp/shrri_ss.png")
        return browser_action(action, url=url, selector=selector, text=text, submit=submit, path=path)
    if tool == "briefing":
        from tools.briefing_tool import get_briefing
        return get_briefing()

    if tool == "wa_read":
        from tools.whatsapp_reader import read_whatsapp
        return read_whatsapp(params.get("query", message))

    if tool == "pyexec":
        from tools.python_tool import run_python
        return run_python(params.get("query", message))

    if tool == "pyexec":
        from tools.python_tool import run_python
        return run_python(params.get("query", message))

    if tool == "youtube":
        from tools.youtube_tool import summarize_youtube
        return summarize_youtube(params.get("query", message))

    if tool == "files":
        from tools.file_tool import file_search, open_file
        if action == "open":
            return open_file(params.get("query", message))
        return file_search(params.get("query", message))

    if tool == "system":
        from tools.system_tool import system_control
        return system_control(params.get("query", message))

    if tool == "notes":
        from tools.notes_tool import save_note, show_notes, delete_note
        if action == "save":
            return save_note(params.get("query", message))
        if action == "delete":
            return delete_note(params.get("query", message))
        return show_notes(params.get("query", message))

    if tool == "reminder":
        from tools.reminder_tool import set_reminder, list_reminders, delete_all_reminders, delete_reminder
        if action == "list":
            return list_reminders()
        if action == "delete_all":
            return delete_all_reminders()
        if action == "delete_one":
            import re as _re
            _q = params.get("query", message)
            _kw = _re.sub(r'^(delete|remove|cancel)\s+(reminder|remind)\s*(for|about)?\s*', '', _q, flags=_re.IGNORECASE).strip()
            return delete_reminder(_kw or _q)
        return set_reminder(params.get("query", message))

    if tool == "calendar":
        from tools.calendar_tool import get_today_events, get_upcoming_events, get_events_for_date
        if action == "today":
            return get_today_events()
        if action == "date":
            from dateparser.search import search_dates
            results = search_dates(
                params.get("query", message),
                settings={"PREFER_DATES_FROM": "future", "TIMEZONE": "Asia/Kolkata", "TO_TIMEZONE": "Asia/Kolkata", "RETURN_AS_TIMEZONE_AWARE": True},
                languages=["en"],
            )
            if not results:
                return "GAP: couldn't understand which date you meant."
            _, target = results[-1]
            return get_events_for_date(target.date())
        if action == "create":
            from tools.calendar_tool import create_event_full
            import json, re as _re
            from engine.router import Router as _R; _r = _R()
            _q = params.get("query", message)
            _p = f"""Extract event details from: "{_q}"
Reply ONLY as JSON: {{"title": "", "date": "", "time": "", "duration_hours": 1.0, "location": "", "description": ""}}
Examples:
- "create event team meeting tomorrow at 2pm" -> {{"title":"team meeting","date":"tomorrow","time":"2pm","duration_hours":1.0,"location":"","description":""}}
- "add dentist appointment friday 10am at Apollo for 2 hours" -> {{"title":"dentist appointment","date":"friday","time":"10am","duration_hours":2.0,"location":"Apollo","description":""}}
- "schedule project review today 3pm" -> {{"title":"project review","date":"today","time":"3pm","duration_hours":1.0,"location":"","description":""}}
IMPORTANT: title should be the event name only, NOT including words like create/add/schedule/event.
Leave fields empty if not mentioned. duration_hours default 1.0."""
            try:
                _raw = _re.sub(r"```json|```", "", _r.chat(_p, task="fast", web_search=False)).strip()
                _d = json.loads(_raw)
                return create_event_full(
                    title=_d.get("title","New Event"),
                    date_str=_d.get("date","today"),
                    time_str=_d.get("time","9am"),
                    duration_hours=float(_d.get("duration_hours",1.0)),
                    location=_d.get("location",""),
                    description=_d.get("description","")
                )
            except Exception as e:
                from tools.calendar_tool import create_event
                return create_event(_q)
        if action == "delete":
            from tools.calendar_tool import delete_event
            import re as _re
            _q = params.get("query", message)
            # Extract keyword — strip command words
            _kw = _re.sub(r'^(delete|cancel|remove)\s+(event|meeting|appointment)?\s*', '', _q, flags=_re.IGNORECASE).strip()
            return delete_event(_kw or _q)
        if action == "update":
            from tools.calendar_tool import update_event
            import json, re as _re
            from engine.router import Router as _R; _r = _R()
            _q = params.get("query", message)
            # Pre-strip command words before LLM
            import re as _re2
            _q_clean = _re2.sub(r'^(update|edit|change|reschedule|rename)\s+(event|meeting|appointment)?\s*', '', _q, flags=_re2.IGNORECASE).strip()
            _p = f"""Extract from: "{_q_clean}"
Reply ONLY as JSON: {{"query": "short keyword to find event (1-3 words, event name only)", "new_title": "", "new_time": "", "new_location": "", "new_description": ""}}
Examples:
- "update team meeting to 4pm" -> {{"query":"team meeting","new_title":"","new_time":"4pm","new_location":"","new_description":""}}
- "reschedule dentist to tomorrow 11am" -> {{"query":"dentist","new_title":"","new_time":"11am","new_location":"","new_description":""}}
- "rename project review to sprint review" -> {{"query":"project review","new_title":"sprint review","new_time":"","new_location":"","new_description":""}}
Leave fields empty if not mentioned."""
            try:
                _raw = _re.sub(r"```json|```", "", _r.chat(_p, task="fast", web_search=False)).strip()
                _d = json.loads(_raw)
                return update_event(
                    _d.get("query", _q_clean),
                    new_title=_d.get("new_title",""),
                    new_time=_d.get("new_time",""),
                    new_location=_d.get("new_location",""),
                    new_description=_d.get("new_description","")
                )
            except Exception as e:
                return f"Update parse error: {e}"
        if action == "search":
            from tools.calendar_tool import search_events
            import re as _re
            _q = params.get("query", message)
            _kw = _re.sub(r'^(search|find|look up|show)\s+(my\s+)?(calendar\s+)?(for\s+)?', '', _q, flags=_re.IGNORECASE).strip()
            return search_events(_kw or _q)
        if action == "recurring":
            from tools.calendar_tool import create_recurring_event
            import json, re as _re
            from engine.router import Router as _R; _r = _R()
            _q = params.get("query", message)
            _p = f"""Extract recurring event details from: "{_q}"
Reply ONLY as JSON: {{"title":"","date":"","time":"","recurrence":"weekly","count":4,"location":"","description":""}}
recurrence must be: daily, weekly, or monthly. count = number of occurrences.
Examples:
- "create weekly standup every monday 9am for 8 weeks" -> {{"title":"standup","date":"monday","time":"9am","recurrence":"weekly","count":8,"location":"","description":""}}
- "add daily workout at 6am for 30 days" -> {{"title":"workout","date":"today","time":"6am","recurrence":"daily","count":30,"location":"","description":""}}"""
            try:
                import re as _re2
                _raw = _re2.sub(r"```json|```", "", _r.chat(_p, task="fast", web_search=False)).strip()
                _d = json.loads(_raw)
                return create_recurring_event(
                    title=_d.get("title","Event"),
                    date_str=_d.get("date","today"),
                    time_str=_d.get("time","9am"),
                    recurrence=_d.get("recurrence","weekly"),
                    count=int(_d.get("count",4)),
                    location=_d.get("location",""),
                    description=_d.get("description","")
                )
            except Exception as e:
                return f"Recurring event error: {e}"
        return get_upcoming_events(params.get("days", 7))

    if tool == "weather":
        from tools.weather_tool import get_weather
        import re as _wr
        DEFAULT_LOCATION = "Chennai"  # change to your home city if needed
        TRAILING_FILLER = [
            "right now", "right", "now", "today", "currently", "please",
            "at the moment", "outside", "over there",
        ]
        _wm = _wr.search(r"(?:weather|temp|temperature|forecast)\s+(?:in|for|at)\s+(.+)", params.get("query", message), _wr.IGNORECASE)
        if _wm:
            candidate = _wm.group(1).strip()
            # Strip trailing filler words/phrases (longest first) since they're
            # part of natural question phrasing, not the place name itself.
            changed = True
            while changed:
                changed = False
                lowered = candidate.lower().strip()
                for filler in sorted(TRAILING_FILLER, key=len, reverse=True):
                    if lowered.endswith(filler):
                        candidate = candidate[: len(candidate) - len(filler)].strip(" ?.,!")
                        changed = True
                        break
            # Reject only if what's LEFT after stripping still looks like a
            # question word rather than a place name.
            bad_words = {"eppadi", "iruku", "how", "is", "it"}
            words = candidate.lower().split()
            if candidate and not any(w in bad_words for w in words) and len(candidate) < 40:
                location = candidate
            else:
                location = DEFAULT_LOCATION
        else:
            location = DEFAULT_LOCATION
        return get_weather(location)

    if tool == "math":
        from tools.math_tool import extract_and_calculate
        return extract_and_calculate(params.get("query", message))

    if tool == "date":
        from tools.time_tool import get_current_date
        return get_current_date()

    if tool == "time":
        from tools.time_tool import get_current_time
        return get_current_time()

    if tool == "gmail":
        from tools.gmail import read_emails, search_emails, send_email

        if action == "read":
            return read_emails(max_results=params.get("max_results", 5))

        elif action == "read_body":
            from tools.gmail import list_recent_subjects, read_email_body_by_id

            user_query = params.get("query", "")
            subjects = list_recent_subjects(max_results=20, query="in:all")

            if not subjects:
                return "GAP: no recent emails found to match against for read_body"

            # --- Step 1: cheap keyword pre-filter, no LLM call needed ---
            STOPWORDS = {
                "the", "mail", "email", "about", "explain", "open", "show",
                "what", "does", "this", "that", "full", "read", "body",
            }
            query_words = [
                w.lower().strip(".,!?") for w in user_query.split()
                if len(w) > 3 and w.lower() not in STOPWORDS
            ]

            keyword_matches = []
            for i, s in enumerate(subjects):
                subject_lower = s["subject"].lower()
                if any(w in subject_lower for w in query_words):
                    keyword_matches.append(i)

            match_index = None
            if len(keyword_matches) == 1:
                match_index = keyword_matches[0]

            # --- Step 2: fall back to LLM matching only if ambiguous ---
            if match_index is None:
                listing = "\n".join(
                    f"{i}. From: {s['sender']} | Subject: {s['subject']}"
                    for i, s in enumerate(subjects)
                )
                try:
                    from engine.router import Router
                    router = Router()
                    match_prompt = (
                        f"The user asked: \"{user_query}\"\n\n"
                        f"Recent emails:\n{listing}\n\n"
                        f"Reply with ONLY the single digit number of the email that "
                        f"best matches what the user is asking about. "
                        f"Look carefully at every subject line before deciding. "
                        f"If genuinely none match, reply exactly: -1\n"
                        f"Your reply must be ONLY a number, nothing else."
                    )
                    reply = router.chat(match_prompt, task="fast", web_search=False)
                    digits = "".join(c for c in reply.strip() if c.isdigit() or c == "-")
                    match_index = int(digits) if digits else -1
                except Exception as e:
                    return f"GAP: read_body LLM matching failed — {e}"

            if match_index is None or match_index < 0 or match_index >= len(subjects):
                return f"GAP: no confident match found for '{user_query}' among recent email subjects"

            matched_email = subjects[match_index]
            return read_email_body_by_id(matched_email["id"])

        elif action == "send":
            to = params.get("to", "")
            subject = params.get("subject", "Message from SHRRI")
            body = params.get("body", "")
            if not to:
                return "❌ No recipient found. Please include an email address."
            return send_email(to=to, subject=subject, body=body)

        elif action == "reply":
            from tools.gmail import reply_email, list_recent_subjects
            user_query = params.get("query", "")
            subjects = list_recent_subjects(max_results=10)
            if not subjects:
                return "No recent emails to reply to."
            reply_body = user_query
            for kw in ["reply to", "respond to", "tell them", "say that"]:
                if kw in user_query.lower():
                    reply_body = user_query.lower().split(kw, 1)[-1].strip()
                    break
            listing = "\n".join(f"{i}. {s['sender']} | {s['subject']}" for i, s in enumerate(subjects))
            try:
                from engine.router import Router as _R; _r = _R()
                _p = f"Which email to reply to? Message: \"{user_query}\"\n{listing}\nReply ONLY with index number or -1."
                _d = "".join(ch for ch in _r.chat(_p, task="fast", web_search=False).strip() if ch.isdigit() or ch=="-")
                idx = int(_d) if _d else 0
            except Exception: idx = 0
            if idx < 0 or idx >= len(subjects): return "Could not find which email to reply to."
            return reply_email(subjects[idx]["id"], reply_body)
        elif action == "archive":
            from tools.gmail import archive_email, list_recent_subjects
            subjects = list_recent_subjects(max_results=5)
            if not subjects: return "No recent emails found."
            return archive_email(subjects[0]["id"])
        elif action == "delete":
            from tools.gmail import delete_email, list_recent_subjects
            subjects = list_recent_subjects(max_results=5)
            if not subjects: return "No recent emails found."
            return delete_email(subjects[0]["id"])
        elif action == "mark_read":
            from tools.gmail import mark_as_read, list_recent_subjects
            subjects = list_recent_subjects(max_results=5)
            if not subjects: return "No recent emails found."
            return mark_as_read(subjects[0]["id"])
        elif action == "draft":
            from tools.gmail import save_draft
            _to = params.get("to", "")
            _subj = params.get("subject", "Draft")
            _body = params.get("body", "")
            if _to and _body:
                return save_draft(_to, _subj, _body)
            import json, re
            from engine.router import Router as _R2; _r2 = _R2()
            _q = params.get("query", "")
            try:
                _raw = re.sub(r"```json|```", "", _r2.chat(f"Extract to,subject,body from: \"{_q}\". JSON only: {{\"to\":\"\",\"subject\":\"\",\"body\":\"\"}}", task="fast", web_search=False)).strip()
                _d2 = json.loads(_raw)
                return save_draft(_d2.get("to",""), _d2.get("subject","Draft"), _d2.get("body",""))
            except Exception as e: return f"Draft error: {e}"
        elif action == "attachment":
            from tools.gmail import download_attachments, list_recent_subjects
            subjects = list_recent_subjects(max_results=5)
            if not subjects: return "No recent emails found."
            return download_attachments(subjects[0]["id"])
        elif action == "search":
            return search_emails(query=params.get("query", ""), max_results=5)

    return ""
