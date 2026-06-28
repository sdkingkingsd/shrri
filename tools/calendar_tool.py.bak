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

def create_event(message: str) -> str:
    """Parse natural language and create a calendar event."""
    try:
        import re
        from googleapiclient.discovery import build
        from tools.gmail import get_gmail_service
        creds = get_gmail_service()._http.credentials
        service = build("calendar", "v3", credentials=creds)

        tz = pytz.timezone("Asia/Kolkata")
        now = datetime.now(tz)

        # Extract time
        time_match = re.search(r'at\s+(\d{1,2})(?:[:.:](\d{2}))?\s*(am|pm)?', message, re.IGNORECASE)
        hour, minute = 9, 0
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            period = time_match.group(3)
            if period and period.lower() == 'pm' and hour != 12:
                hour += 12
            if period and period.lower() == 'am' and hour == 12:
                hour = 0

        # Extract date
        msg = message.lower()
        if 'tomorrow' in msg:
            event_date = now + timedelta(days=1)
        elif 'today' in msg:
            event_date = now
        elif 'next week' in msg:
            event_date = now + timedelta(days=7)
        else:
            day_match = re.search(r'on\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', msg)
            if day_match:
                days_map = {'monday':0,'tuesday':1,'wednesday':2,'thursday':3,'friday':4,'saturday':5,'sunday':6}
                target = days_map[day_match.group(1)]
                current = now.weekday()
                diff = (target - current) % 7 or 7
                event_date = now + timedelta(days=diff)
            else:
                event_date = now + timedelta(days=1)

        # Extract title
        title = "Meeting"
        for marker in ["add ", "create ", "schedule ", "set up ", "book "]:
            idx = msg.find(marker)
            if idx != -1:
                rest = msg[idx+len(marker):]
                # Remove time/date parts
                rest = re.sub(r'(tomorrow|today|next week|on \w+|at \d+.*)', '', rest).strip()
                if rest:
                    title = rest.title()
                break

        start_dt = event_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        end_dt = start_dt + timedelta(hours=1)

        event = {
            'summary': title,
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
            'end':   {'dateTime': end_dt.isoformat(),   'timeZone': 'Asia/Kolkata'},
        }
        result = service.events().insert(calendarId='primary', body=event).execute()
        return f"📅 Event created: '{result['summary']}' on {start_dt.strftime('%a %b %d at %I:%M %p')}"

    except Exception as e:
        return f"GAP: could not create event — {e}"
