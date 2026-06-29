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
- weather: get weather information
- calendar_today: check today's schedule/events
- calendar_date: check schedule for a specific day (tomorrow, a weekday name, or a specific date)
- calendar_upcoming: check upcoming/this week's events
- calendar_create: create/add a new event or meeting
- reminder_set: set a reminder or alert
- reminder_list: show existing reminders
- reminder_delete: delete all reminders or clear all reminders
- notes_save: save/add/remember a note
- notes_show: show/list/find notes
- notes_delete: delete a note
- briefing: morning/daily briefing or summary
- news: get latest news or current events
- files: find/search/open files on computer
- system: system controls like shutdown, lock screen
- schedule_add: schedule an automated recurring task
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
    elif tool == "reminder_set":
        return {"tool": "reminder", "action": "set", "params": {"query": message}}
    elif tool == "reminder_list":
        return {"tool": "reminder", "action": "list", "params": {}}
    elif tool == "reminder_delete":
        return {"tool": "reminder", "action": "delete_all", "params": {}}
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
        from tools.whatsapp_tool import send_whatsapp
        result = send_whatsapp(params.get("query", message))
        return result

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
        from tools.reminder_tool import set_reminder, list_reminders, delete_all_reminders
        if action == "list":
            return list_reminders()
        if action == "delete_all":
            return delete_all_reminders()
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
            from tools.calendar_tool import create_event
            return create_event(params.get("query", message))
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
            subjects = list_recent_subjects(max_results=10, query="")

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

        elif action == "search":
            return search_emails(query=params.get("query", ""), max_results=5)

    return ""
