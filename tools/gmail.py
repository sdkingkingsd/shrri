import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

CREDENTIALS_FILE = os.path.expanduser("~/.shrri/gmail_credentials.json")
TOKEN_FILE = os.path.expanduser("~/.shrri/gmail_token.json")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.modify",
]


def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def read_emails(max_results=5, query="is:unread"):
    try:
        service = get_gmail_service()
        results = service.users().messages().list(
            userId="me", maxResults=max_results, q=query
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return "No emails found."

        output = f"📧 Gmail — {len(messages)} emails found:\n"
        output += "=" * 50 + "\n"

        for msg in messages:
            msg_data = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()

            headers = msg_data.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
            date = next((h["value"] for h in headers if h["name"] == "Date"), "Unknown")

            output += f"\n📩 From: {sender}\n"
            output += f"   Subject: {subject}\n"
            output += f"   Date: {date}\n"

        return output[:1500]

    except Exception as e:
        return f"Gmail error: {str(e)}"


def list_recent_subjects(max_results=10, query=""):
    """List recent email subjects with their Gmail message IDs — cheap, metadata-only call."""
    try:
        service = get_gmail_service()
        results = service.users().messages().list(
            userId="me", maxResults=max_results, q=query
        ).execute()

        messages = results.get("messages", [])
        items = []
        for msg in messages:
            msg_data = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "Subject"]
            ).execute()
            headers = msg_data.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
            items.append({"id": msg["id"], "subject": subject, "sender": sender})
        return items
    except Exception as e:
        print(f"[Gmail] list_recent_subjects error: {e}")
        return []


def read_email_body_by_id(message_id: str) -> str:
    """Read the full body of a specific email by its exact Gmail message ID."""
    try:
        service = get_gmail_service()
        msg_data = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()

        headers = msg_data.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")

        body = ""
        payload = msg_data.get("payload", {})
        parts = payload.get("parts", [])

        if parts:
            for part in parts:
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                        break
        else:
            data = payload.get("body", {}).get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

        body = body.strip()[:800]
        return f"📩 From: {sender}\nSubject: {subject}\n\n{body}"

    except Exception as e:
        return f"Error reading email body: {str(e)}"


def read_email_body(query: str = "is:unread", index: int = 0) -> str:
    try:
        service = get_gmail_service()
        results = service.users().messages().list(
            userId="me", maxResults=10, q=query
        ).execute()

        messages = results.get("messages", [])
        if not messages or index >= len(messages):
            return "Email not found."

        msg_data = service.users().messages().get(
            userId="me", id=messages[index]["id"], format="full"
        ).execute()

        headers = msg_data.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")

        body = ""
        payload = msg_data.get("payload", {})
        parts = payload.get("parts", [])

        if parts:
            for part in parts:
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                        break
        else:
            data = payload.get("body", {}).get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

        body = body.strip()[:800]

        return f"📩 From: {sender}\nSubject: {subject}\n\n{body}"

    except Exception as e:
        return f"Error reading email body: {str(e)}"


def send_email(to: str, subject: str, body: str):
    try:
        service = get_gmail_service()

        message = MIMEMultipart()
        message["to"] = to
        message["subject"] = subject
        message.attach(MIMEText(body, "plain"))

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

        return f"✅ Email sent to {to} — Subject: {subject}"

    except Exception as e:
        return f"Gmail send error: {str(e)}"


def search_emails(query: str, max_results=5):
    return read_emails(max_results=max_results, query=query)


if __name__ == "__main__":
    print("Testing Gmail connection...")
    print(read_emails(max_results=3))

def read_latest_body(n=1):
    """Read the actual full body of the latest n emails."""
    try:
        service = get_gmail_service()
        results = service.users().messages().list(
            userId="me", maxResults=n, q="is:unread"
        ).execute()
        messages = results.get("messages", [])
        if not messages:
            results = service.users().messages().list(
                userId="me", maxResults=n
            ).execute()
            messages = results.get("messages", [])
        if not messages:
            return "No emails found."

        output = []
        for msg in messages[:n]:
            msg_data = service.users().messages().get(
                userId="me", id=msg["id"], format="full"
            ).execute()
            headers = {h["name"]: h["value"] for h in msg_data["payload"]["headers"]}
            subject = headers.get("Subject", "No subject")
            sender = headers.get("From", "Unknown")
            date = headers.get("Date", "")

            # Extract body — try plain text first, then HTML
            body = ""
            payload = msg_data["payload"]
            html_body = ""

            def extract_parts(parts):
                global_plain = ""
                global_html = ""
                for part in parts:
                    mime = part.get("mimeType", "")
                    if mime == "text/plain":
                        data = part["body"].get("data", "")
                        if data:
                            global_plain += base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    elif mime == "text/html":
                        data = part["body"].get("data", "")
                        if data:
                            global_html += base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    elif "parts" in part:
                        p, h = extract_parts(part["parts"])
                        global_plain += p
                        global_html += h
                return global_plain, global_html

            if "parts" in payload:
                body, html_body = extract_parts(payload["parts"])
            elif "body" in payload:
                data = payload["body"].get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

            # If no plain text, strip HTML tags
            if not body.strip() and html_body:
                import re as _re
                body = _re.sub(r"<[^>]+>", " ", html_body)
                body = _re.sub(r"\s+", " ", body).strip()

            body = body.strip()[:1500] if body else "(no body content)"
            output.append(f"From: {sender}\nSubject: {subject}\nDate: {date}\n\n{body}")

        return "\n\n---\n\n".join(output)
    except Exception as e:
        return f"Error reading email body: {e}"

def reply_email(message_id: str, reply_body: str) -> str:
    try:
        import base64
        from email.mime.text import MIMEText
        service = get_gmail_service()
        # Get original message for threading
        orig = service.users().messages().get(userId="me", id=message_id, format="metadata",
               metadataHeaders=["Subject","From","Message-ID"]).execute()
        headers = orig.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "Re:")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "")
        msg_id = next((h["value"] for h in headers if h["name"] == "Message-ID"), "")
        if not subject.startswith("Re:"):
            subject = "Re: " + subject
        msg = MIMEText(reply_body)
        msg["To"] = sender
        msg["Subject"] = subject
        msg["In-Reply-To"] = msg_id
        msg["References"] = msg_id
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        thread_id = orig.get("threadId", "")
        service.users().messages().send(userId="me", body={"raw": raw, "threadId": thread_id}).execute()
        return f"✅ Reply sent to {sender}"
    except Exception as e:
        return f"Reply error: {e}"

def mark_as_read(message_id: str) -> str:
    try:
        service = get_gmail_service()
        service.users().messages().modify(userId="me", id=message_id,
            body={"removeLabelIds": ["UNREAD"]}).execute()
        return "✅ Marked as read"
    except Exception as e:
        return f"Error: {e}"

def archive_email(message_id: str) -> str:
    try:
        service = get_gmail_service()
        service.users().messages().modify(userId="me", id=message_id,
            body={"removeLabelIds": ["INBOX"]}).execute()
        return "✅ Archived"
    except Exception as e:
        return f"Error: {e}"

def delete_email(message_id: str) -> str:
    try:
        service = get_gmail_service()
        service.users().messages().trash(userId="me", id=message_id).execute()
        return "✅ Moved to trash"
    except Exception as e:
        return f"Error: {e}"

def save_draft(to: str, subject: str, body: str) -> str:
    try:
        import base64
        from email.mime.text import MIMEText
        service = get_gmail_service()
        msg = MIMEText(body)
        msg["To"] = to
        msg["Subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
        return f"✅ Draft saved — To: {to}, Subject: {subject}"
    except Exception as e:
        return f"Draft error: {e}"

def download_attachments(message_id: str, save_dir="~/Downloads") -> str:
    try:
        import base64
        service = get_gmail_service()
        save_dir = os.path.expanduser(save_dir)
        os.makedirs(save_dir, exist_ok=True)
        msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        parts = msg.get("payload", {}).get("parts", [])
        saved = []
        for part in parts:
            filename = part.get("filename", "")
            if not filename:
                continue
            body = part.get("body", {})
            att_id = body.get("attachmentId")
            if att_id:
                att = service.users().messages().attachments().get(
                    userId="me", messageId=message_id, id=att_id).execute()
                data = base64.urlsafe_b64decode(att["data"])
            elif body.get("data"):
                data = base64.urlsafe_b64decode(body["data"])
            else:
                continue
            path = os.path.join(save_dir, filename)
            with open(path, "wb") as f:
                f.write(data)
            saved.append(filename)
        if saved:
            return "✅ Downloaded: " + ", ".join(saved) + f"\nSaved to: {save_dir}"
        return "No attachments found."
    except Exception as e:
        return f"Attachment error: {e}"
