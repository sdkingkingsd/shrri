"""Google Calendar tool — read events."""
from datetime import datetime, timedelta
import pytz

def get_today_events() -> str:
    try:
        from googleapiclient.discovery import build
        from tools.gmail import get_gmail_service
        creds = get_gmail_service()._http.credentials
        service = build("calendar", "v3", credentials=creds)
        tz = pytz.timezone("Asia/Kolkata")
        now = datetime.now(tz)
        start = now.replace(hour=0, minute=0, second=0).isoformat()
        end = now.replace(hour=23, minute=59, second=59).isoformat()
        events = service.events().list(
            calendarId="primary", timeMin=start, timeMax=end,
            singleEvents=True, orderBy="startTime"
        ).execute().get("items", [])
        if not events:
            return "No events scheduled for today."
        lines = ["Today's events:"]
        for e in events:
            start_t = e["start"].get("dateTime", e["start"].get("date", ""))
            t = datetime.fromisoformat(start_t).strftime("%I:%M %p") if "T" in start_t else "All day"
            lines.append(f"  - {t}: {e.get('summary', 'No title')}")
        return "\n".join(lines)
    except Exception as ex:
        return f"GAP: calendar error — {ex}"

def get_upcoming_events(days=7) -> str:
    try:
        from googleapiclient.discovery import build
        from tools.gmail import get_gmail_service
        creds = get_gmail_service()._http.credentials
        service = build("calendar", "v3", credentials=creds)
        tz = pytz.timezone("Asia/Kolkata")
        now = datetime.now(tz)
        end = (now + timedelta(days=days)).isoformat()
        events = service.events().list(
            calendarId="primary", timeMin=now.isoformat(), timeMax=end,
            singleEvents=True, orderBy="startTime", maxResults=10
        ).execute().get("items", [])
        if not events:
            return f"No events in the next {days} days."
        lines = [f"Upcoming events ({days} days):"]
        for e in events:
            start_t = e["start"].get("dateTime", e["start"].get("date", ""))
            t = datetime.fromisoformat(start_t).strftime("%a %b %d, %I:%M %p") if "T" in start_t else start_t
            lines.append(f"  - {t}: {e.get('summary', 'No title')}")
        return "\n".join(lines)
    except Exception as ex:
        return f"GAP: calendar error — {ex}"
