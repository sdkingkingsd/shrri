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
                dt = datetime.fromisoformat(start_info.replace('Z', '+00:00'))
                dt = dt.astimezone(IST)
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
                dt = datetime.fromisoformat(start_info.replace('Z', '+00:00'))
                dt = dt.astimezone(IST)
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


def search_events(query: str, max_results: int = 10) -> str:
    """Search events by keyword."""
    try:
        service = _get_service()
        now = datetime.now(IST)
        end = now + timedelta(days=365)
        results = service.events().list(
            calendarId='primary',
            q=query,
            timeMin=now.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy='startTime',
            maxResults=max_results
        ).execute()
        events = results.get('items', [])
        if not events:
            return f"No events found matching '{query}'."
        lines = [f"Search results for '{query}':"]
        for event in events:
            start_info = event['start'].get('dateTime', event['start'].get('date'))
            if 'T' in start_info:
                dt = datetime.fromisoformat(start_info.replace('Z', '+00:00')).astimezone(IST)
                time_str = dt.strftime('%a %d %b, %I:%M %p')
            else:
                time_str = start_info + " (All day)"
            summary = event.get('summary', 'No title')
            eid = event.get('id', '')
            lines.append(f"  - {time_str} - {summary} [ID:{eid[:8]}]")
        return "\n".join(lines)
    except Exception as e:
        return f"GAP: search failed - {e}"


def delete_event(query: str) -> str:
    """Delete/cancel an event by keyword match."""
    try:
        service = _get_service()
        now = datetime.now(IST)
        end = now + timedelta(days=365)
        results = service.events().list(
            calendarId='primary',
            q=query,
            timeMin=now.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy='startTime',
            maxResults=5
        ).execute()
        events = results.get('items', [])
        if not events:
            return f"No upcoming events found matching '{query}'."
        event = events[0]
        summary = event.get('summary', 'No title')
        eid = event.get('id')
        service.events().delete(calendarId='primary', eventId=eid).execute()
        return f"Deleted event: {summary}"
    except Exception as e:
        return f"GAP: delete failed - {e}"


def update_event(query: str, new_title: str = "", new_time: str = "", new_location: str = "", new_description: str = "") -> str:
    """Update an existing event by keyword match."""
    try:
        import re
        service = _get_service()
        now = datetime.now(IST)
        end = now + timedelta(days=365)
        results = service.events().list(
            calendarId='primary',
            q=query,
            timeMin=now.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy='startTime',
            maxResults=5
        ).execute()
        events = results.get('items', [])
        if not events:
            return f"No upcoming events found matching '{query}'."
        event = events[0]
        original = event.get('summary', 'event')
        if new_title:
            event['summary'] = new_title
        if new_location:
            event['location'] = new_location
        if new_description:
            event['description'] = new_description
        if new_time:
            tm = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', new_time.lower())
            if tm:
                hour = int(tm.group(1))
                minute = int(tm.group(2)) if tm.group(2) else 0
                period = tm.group(3)
                if period == 'pm' and hour != 12: hour += 12
                if period == 'am' and hour == 12: hour = 0
                old_start = event['start'].get('dateTime', '')
                if old_start:
                    old_dt = datetime.fromisoformat(old_start.replace('Z', '+00:00')).astimezone(IST)
                    new_start = old_dt.replace(hour=hour, minute=minute)
                    new_end = new_start + timedelta(hours=1)
                    event['start'] = {'dateTime': new_start.isoformat(), 'timeZone': 'Asia/Kolkata'}
                    event['end'] = {'dateTime': new_end.isoformat(), 'timeZone': 'Asia/Kolkata'}
        service.events().update(calendarId='primary', eventId=event['id'], body=event).execute()
        return f"Updated '{original}' - changes saved."
    except Exception as e:
        return f"GAP: update failed - {e}"


def create_event_full(title: str, date_str: str, time_str: str, duration_hours: float = 1.0,
                      location: str = "", description: str = "") -> str:
    """Create event with full details."""
    try:
        import re
        from dateparser import parse as dp
        now = datetime.now(IST)
        parsed_date = dp(date_str, settings={"PREFER_DATES_FROM": "future", "TIMEZONE": "Asia/Kolkata"})
        event_date = parsed_date.date() if parsed_date else now.date()
        tm = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', time_str.lower())
        hour, minute = 9, 0
        if tm:
            hour = int(tm.group(1))
            minute = int(tm.group(2)) if tm.group(2) else 0
            period = tm.group(3)
            if period == 'pm' and hour != 12: hour += 12
            if period == 'am' and hour == 12: hour = 0
        start_dt = IST.localize(datetime.combine(event_date, datetime.min.time().replace(hour=hour, minute=minute)))
        end_dt = start_dt + timedelta(hours=duration_hours)
        body = {
            'summary': title,
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
        }
        if location: body['location'] = location
        if description: body['description'] = description
        service = _get_service()
        service.events().insert(calendarId='primary', body=body).execute()
        loc_str = f" at {location}" if location else ""
        return f"Event created: {title}{loc_str} on {start_dt.strftime('%d %b at %I:%M %p')}"
    except Exception as e:
        return f"GAP: could not create event - {e}"


def create_recurring_event(title: str, date_str: str, time_str: str,
                            recurrence: str = "weekly", count: int = 4,
                            location: str = "", description: str = "") -> str:
    """Create a recurring event — daily/weekly/monthly."""
    try:
        import re
        from dateparser import parse as dp
        now = datetime.now(IST)
        parsed_date = dp(date_str, settings={"PREFER_DATES_FROM": "future", "TIMEZONE": "Asia/Kolkata"})
        event_date = parsed_date.date() if parsed_date else now.date()
        tm = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', time_str.lower())
        hour, minute = 9, 0
        if tm:
            hour = int(tm.group(1))
            minute = int(tm.group(2)) if tm.group(2) else 0
            period = tm.group(3)
            if period == 'pm' and hour != 12: hour += 12
            if period == 'am' and hour == 12: hour = 0
        start_dt = IST.localize(datetime.combine(event_date,
                    datetime.min.time().replace(hour=hour, minute=minute)))
        end_dt = start_dt + timedelta(hours=1)
        freq_map = {"daily": "DAILY", "weekly": "WEEKLY", "monthly": "MONTHLY"}
        freq = freq_map.get(recurrence.lower(), "WEEKLY")
        body = {
            'summary': title,
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Kolkata'},
            'recurrence': [f'RRULE:FREQ={freq};COUNT={count}'],
        }
        if location: body['location'] = location
        if description: body['description'] = description
        service = _get_service()
        service.events().insert(calendarId='primary', body=body).execute()
        return f"Recurring event created: {title} - {recurrence} x{count} starting {start_dt.strftime('%d %b at %I:%M %p')}"
    except Exception as e:
        return f"GAP: could not create recurring event - {e}"
