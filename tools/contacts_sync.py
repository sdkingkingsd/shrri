"""Google Contacts (People API) sync — lookup and save contact phone
numbers, so SHRRI can resolve names to numbers without the number ever
being typed into chat or stored as a visible 'fact' the LLM might recite.

Auth follows the same pattern as tools/gmail.py, but uses its own token
file (separate scope, separate consent) -- the existing Gmail/Calendar
token is untouched.
"""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

CREDENTIALS_FILE = os.path.expanduser("~/.shrri/gmail_credentials.json")
TOKEN_FILE = os.path.expanduser("~/.shrri/contacts_token.json")
SCOPES = ["https://www.googleapis.com/auth/contacts"]


def _get_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("people", "v1", credentials=creds)


def lookup_number(name: str):
    """Search Google Contacts for a name (substring match), return the
    first matching phone number (digits only, no +), or None if not found."""
    try:
        service = _get_service()
        results = service.people().searchContacts(
            query=name,
            readMask="names,phoneNumbers",
        ).execute()
        matches = results.get("results", [])
        if not matches:
            return None
        person = matches[0].get("person", {})
        phones = person.get("phoneNumbers", [])
        if not phones:
            return None
        raw = phones[0].get("value", "")
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            return None
        # Google Contacts often stores Indian numbers without a country
        # code (just the 10-digit local number). Assume +91 in that case
        # -- adjust here if you start adding international contacts.
        if len(digits) == 10:
            digits = "91" + digits
        return digits
    except Exception:
        return None


def save_number(name: str, phone: str) -> bool:
    """Save a new contact to Google Contacts. phone should be digits with
    country code (e.g. 919876543210)."""
    try:
        service = _get_service()
        digits = "".join(c for c in phone if c.isdigit())
        body = {
            "names": [{"givenName": name}],
            "phoneNumbers": [{"value": "+" + digits}],
        }
        service.people().createContact(body=body).execute()
        return True
    except Exception:
        return False
