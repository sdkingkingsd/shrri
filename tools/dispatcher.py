import re


def detect_intent(message: str) -> dict:
    msg = message.lower()

    # Read full email body — explain/open specific email
    if any(x in msg for x in ["explain", "open", "show", "read body", "what does", "full email"]):
        if any(x in msg for x in ["email", "mail", "acm", "cisco", "ubs", "philips", "vitcc", "placement", "transport"]):
            return {"tool": "gmail", "action": "read_body", "params": {"query": message}}

    # Send email — all natural human phrases
    send_triggers = [
        "send email", "send mail", "send message", "send this",
        "send it", "send to", "shoot an email", "shoot a mail",
        "write an email", "write a mail", "compose email", "compose mail",
        "draft and send", "forward this", "forward to",
        "mail to", "message to", "email to", "drop a mail",
        "drop an email", "ping them", "ping him", "ping her",
        "reach out to", "send over", "fire an email", "fire a mail",
        "shoot this", "shoot over", "pass this", "pass along",
        "let them know", "notify them", "inform them",
    ]
    if any(t in msg for t in send_triggers) or re.search(r"send .{0,20}to [^\s]+@[^\s]+", msg):
        to = re.search(r"to ([^\s]+@[^\s]+)", msg)
        subject = re.search(r"subject (.+?) body", msg)
        body = re.search(r"body (.+)$", msg, re.DOTALL)
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

    if tool == "gmail":
        from tools.gmail import read_emails, search_emails, read_email_body, send_email

        if action == "read":
            return read_emails(max_results=params.get("max_results", 5))

        elif action == "read_body":
            msg = params.get("query", "").lower()
            keyword_map = {
                "acm": "acm",
                "cisco": "cisco",
                "ubs": "ubs",
                "philips": "philips",
                "transport": "transport",
                "placement": "placement",
                "vitcc": "vitcc",
            }
            matched = next((v for k, v in keyword_map.items() if k in msg), None)
            query = matched if matched else "is:unread"
            return read_email_body(query=query, index=0)

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
