"""Google Calendar tool — read events."""
from datetime import datetime, timedelta
import pytz

IST = pytz.timezone("Asia/Kolkata")


def _get_service():
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    import os, pickle

    token_path = os.path.expanduser("~/.shrri/calendar_token.pickle")
    with open(token_path, 'rb') as f:
        creds = pickle.load(f)
    return build('calendar', 'v3', credentials=creds)


def _label_for_date(target_date, now) -> str:
    delta = (target_date - now.date()).days
    if delta == 0:
        return "today"
    if delta == 1:
        return "tomorrow"
    return target_date.strftime("%A, %d %b")


def get_events_for_date(target_date) -> str:
    """Get events for any single date. target_date is a date object (IST)."""
    try:
        service = _get_service()
        now = datetime.now(IST)
        label = _label_for_date(target_date, now)

        start = IST.localize(datetime.combine(target_date, datetime.min.time()))
        end = IST.localize(datetime.combine(target_date, datetime.max.time()))

        events_result = service.events().list(
            calendarId='primary',
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        if not events:
            return f"No events scheduled for {label}."

        lines = [f"📅 Events for {label}:"]
        for event in events:
            start_info = event['start'].get('dateTime', event['start'].get('date'))
            if 'T' in start_info:
                dt = datetime.fromisoformat(start_info)
                time_str = dt.strftime('%I:%M %p')
            else:
                time_str = "All day"
            summary = event.get('summary', 'No title')
            lines.append(f"  • {time_str} — {summary}")

        return "\n".join(lines)

    except Exception as e:
        return f"GAP: could not fetch calendar events — {e}"


def get_today_events() -> str:
    """Get today's events. Thin wrapper kept for backward compatibility."""
    return get_events_for_date(datetime.now(IST).date())


def get_upcoming_events(days=7) -> str:
    try:
        service = _get_service()
        now = datetime.now(IST)
        end = now + timedelta(days=days)

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        if not events:
            return f"No events in the next {days} days."

        lines = [f"📅 Upcoming events (next {days} days):"]
        for event in events:
            start_info = event['start'].get('dateTime', event['start'].get('date'))
            if 'T' in start_info:
                dt = datetime.fromisoformat(start_info)
                time_str = dt.strftime('%a %d %b, %I:%M %p')
            else:
                time_str = f"{start_info} (All day)"
            summary = event.get('summary', 'No title')
            lines.append(f"  • {time_str} — {summary}")

        return "\n".join(lines)

    except Exception as e:
        return f"GAP: could not fetch calendar events — {e}"


def create_event(message: str) -> str:
    try:
        import re
        service = _get_service()
        now = datetime.now(IST)
        msg = message.lower()

        if 'tomorrow' in msg:
            event_date = now.date() + timedelta(days=1)
        elif 'today' in msg:
            event_date = now.date()
        else:
            event_date = now.date()

        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', msg)
        hour, minute = 9, 0
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            period = time_match.group(3)
            if period == 'pm' and hour != 12:
                hour += 12
            if period == 'am' and hour == 12:
                hour = 0

        start_dt = IST.localize(datetime.combine(event_date, datetime.min.time().replace(hour=hour, minute=minute)))
        end_dt = start_dt + timedelta(hours=1)

        rest = message
        rest = re.sub(r'(tomorrow|today|next week|on \w+|at \d+.*)', '', rest).strip()
        rest = re.sub(r'^(remind me to|add event|schedule|create event|set up)\b', '', rest, flags=re.IGNORECASE).strip()
        title = rest or "New Event"

        event = {
            'summary': title,
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
        }

        created = service.events().insert(calendarId='primary', body=event).execute()
        return f"📅 Event created: {title} on {start_dt.strftime('%d %b at %I:%M %p')}"

    except Exception as e:
        return f"GAP: could not create event — {e}"
