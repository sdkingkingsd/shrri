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
