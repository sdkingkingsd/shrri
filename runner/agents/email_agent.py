"""
Email Agent — SHRRI AI OS v2 (Phase 5)

Thin wrapper around the existing tools.gmail module, which already
does real Gmail API work (OAuth via the same token as Calendar): read
unread/recent emails, search, send, reply, mark read, archive, delete,
save draft, download attachments. No new email logic here — just
routing the request to the right real function.

Intent routing (checked in order):
  - "send" + to/subject/body            -> send_email
  - "reply" + message id/keyword         -> reply_email (needs id from a
                                             prior read/search in context)
  - "search" + query                     -> search_emails
  - "archive"/"delete"/"mark read" + id  -> corresponding function
  - "draft"/"save draft"                 -> save_draft
  - "download attachment"                -> download_attachments
  - "unread"/"inbox"/default             -> read_emails
  - "latest"/"recent"                    -> list_recent_subjects
"""

import re

from tools import gmail


class EmailAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "").strip()
        low = prompt.lower()
        if self.verbose:
            print(f"[email_agent] Handling: {prompt[:80]!r}")

        # SEND — parse "to X subject Y body Z" style, same convention
        # the existing dispatcher already uses elsewhere in this codebase.
        if "send" in low and re.search(r"\bto\b", low):
            to_match = re.search(r"\bto\s+(\S+@\S+)", prompt, re.IGNORECASE)
            subject_match = re.search(r"\bsubject\s+(.+?)(?:\s+body\s+|$)", prompt, re.IGNORECASE)
            body_match = re.search(r"\bbody\s+(.+)$", prompt, re.IGNORECASE)
            if not to_match:
                return "GAP: I need a recipient email address to send this (e.g. 'mail to x@example.com subject ... body ...')."
            to = to_match.group(1)
            subject = subject_match.group(1).strip() if subject_match else "(no subject)"
            body = body_match.group(1).strip() if body_match else ""
            return gmail.send_email(to, subject, body)

        # SAVE DRAFT
        if "draft" in low:
            to_match = re.search(r"\bto\s+(\S+@\S+)", prompt, re.IGNORECASE)
            subject_match = re.search(r"\bsubject\s+(.+?)(?:\s+body\s+|$)", prompt, re.IGNORECASE)
            body_match = re.search(r"\bbody\s+(.+)$", prompt, re.IGNORECASE)
            if not to_match:
                return "GAP: I need a recipient email address to save this draft."
            to = to_match.group(1)
            subject = subject_match.group(1).strip() if subject_match else "(no subject)"
            body = body_match.group(1).strip() if body_match else ""
            return gmail.save_draft(to, subject, body)

        # SEARCH
        if re.search(r"\b(search|find)\b.*\bemail", low):
            query_match = re.search(r"(?:search|find)\s+(?:for\s+)?(?:emails?\s+)?(?:about\s+|from\s+|containing\s+)?(.+)$", prompt, re.IGNORECASE)
            query = query_match.group(1).strip() if query_match else prompt
            return gmail.search_emails(query)

        # ARCHIVE / DELETE / MARK READ — require a message ID; explain if missing
        id_match = re.search(r"\b(?:id|message)[\s:]+([\w-]{6,})", prompt, re.IGNORECASE)
        if "archive" in low:
            if not id_match:
                return "GAP: tell me which email's message ID to archive (get one from a search/read result)."
            return gmail.archive_email(id_match.group(1))
        if "delete" in low and "email" in low:
            if not id_match:
                return "GAP: tell me which email's message ID to delete (get one from a search/read result)."
            return gmail.delete_email(id_match.group(1))
        if "mark" in low and "read" in low:
            if not id_match:
                return "GAP: tell me which email's message ID to mark as read."
            return gmail.mark_as_read(id_match.group(1))

        # REPLY
        if "reply" in low:
            if not id_match:
                return "GAP: tell me which email's message ID to reply to, and what to say."
            body_match = re.search(r"(?:reply|say|saying)\s*[:\-]?\s*(.+)$", prompt, re.IGNORECASE)
            body = body_match.group(1).strip() if body_match else "Thanks!"
            return gmail.reply_email(id_match.group(1), body)

        # DOWNLOAD ATTACHMENTS
        if "attachment" in low:
            if not id_match:
                return "GAP: tell me which email's message ID has the attachment to download."
            return gmail.download_attachments(id_match.group(1))

        # LATEST / RECENT SUBJECTS
        if re.search(r"\b(latest|recent)\b", low):
            return gmail.list_recent_subjects()

        # Default: unread inbox
        return gmail.read_emails()
