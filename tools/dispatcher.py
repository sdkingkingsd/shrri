import re


def detect_intent(message: str) -> dict:
    msg = message.lower()

    # Deterministic arithmetic — no AI guessing needed. This must run before
    # other checks since a math expression won't match anything else, but we
    # still want it caught early and routed to a real calculator instead of
    # falling through to the LLM, which has proven unreliable at arithmetic
    # (confirmed: invented wrong intermediate results, got stuck in
    # self-contradiction loops trying to "verify" bad math).
    has_arithmetic_symbols = bool(re.search(
        r"\d+\s*(?:[\+\-\*/%\^]|times|multiplied by|plus|minus|divided by)\s*\d+",
        msg
    ))
    if has_arithmetic_symbols:
        return {"tool": "math", "action": "calculate", "params": {"query": message}}

    # Real system time/date — no AI guessing needed
    time_triggers = [
        "what time", "current time", "time now", "what's the time",
        "tell me the time", "what date", "today's date", "what day is it",
        "current date",
    ]
    if any(t in msg for t in time_triggers):
        return {"tool": "time", "action": "get_time", "params": {}}

    # Read full email body — explain/open specific email
    if any(x in msg for x in ["explain", "open", "show", "read body", "what does", "full email"]):
        if any(x in msg for x in ["email", "mail", "acm", "cisco", "ubs", "philips", "vitcc", "placement", "transport"]):
            return {"tool": "gmail", "action": "read_body", "params": {"query": message}}

    # Explicit mail phrases — these unambiguously mean "send an email", even with no
    # address typed yet, so the dispatcher can catch a missing recipient and say so.
    explicit_mail_triggers = [
        "send email", "send mail", "shoot an email", "shoot a mail",
        "write an email", "write a mail", "compose email", "compose mail",
        "mail to", "email to", "drop a mail", "drop an email",
        "fire an email", "fire a mail",
    ]

    # Ambiguous phrases — these could mean a Gmail send OR something else entirely
    # ("send message to chatgpt"), so only treat them as Gmail send if a real
    # email address is actually present in the message.
    ambiguous_send_triggers = [
        "send message", "send this", "send it", "send to",
        "draft and send", "forward this", "forward to", "message to",
        "ping them", "ping him", "ping her", "reach out to", "send over",
        "shoot this", "shoot over", "pass this", "pass along",
        "let them know", "notify them", "inform them",
    ]

    has_email_address = bool(re.search(r"[^\s]+@[^\s]+\.[^\s]+", msg))
    is_explicit_mail = any(t in msg for t in explicit_mail_triggers)
    is_ambiguous_send = any(t in msg for t in ambiguous_send_triggers) or "send" in msg

    if is_explicit_mail or (has_email_address and is_ambiguous_send):
        to = re.search(r"to ([^\s]+@[^\s]+)", message, re.IGNORECASE)
        subject = re.search(r"subject (.+?) body", message, re.IGNORECASE)
        body = re.search(r"body (.+)$", message, re.IGNORECASE | re.DOTALL)
        return {"tool": "gmail", "action": "send", "params": {
            "to": to.group(1) if to else "",
            "subject": subject.group(1).strip() if subject else "Message from SHRRI",
            "body": body.group(1).strip() if body else message
        }}

    # Read inbox
    if any(x in msg for x in [
        "read email", "check email", "my inbox", "unread", "gmail", "emails",
        "any mail", "check mail", "new mail", "new emails", "what emails",
        "got any mail", "any messages", "check messages"
    ]):
        return {"tool": "gmail", "action": "read", "params": {"max_results": 5}}

    # Search email
    if any(x in msg for x in ["search email", "find email", "email from", "email about", "look for email", "find mail"]):
        return {"tool": "gmail", "action": "search", "params": {"query": message}}

    return {"tool": "none", "action": None, "params": {}}


def run_tool(intent: dict, message: str) -> str:
    tool = intent["tool"]
    action = intent["action"]
    params = intent["params"]

    if tool == "math":
        from tools.math_tool import extract_and_calculate
        return extract_and_calculate(params.get("query", message))

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
