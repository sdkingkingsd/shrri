"""
Calendar Agent — SHRRI AI OS v2 (Phase 5)

Thin wrapper around the existing tools.calendar_tool module, which
already does real Google Calendar API work (OAuth via the same token
used for Gmail): read today/upcoming/specific-date events, create
events (with auto Google Meet links), search, update, delete, create
recurring events, and join the next upcoming Meet. No new calendar
logic here — just routing the request to the right real function.

Intent routing (checked in order):
  - "join"/"meet" (join a call)         -> join_meet
  - "delete"/"cancel" + keyword          -> delete_event
  - "update"/"reschedule"/"move" + kw    -> update_event
  - "search"/"find" + keyword            -> search_events
  - "recurring"/"every day/week/month"   -> create_recurring_event
  - "create"/"add"/"schedule" event      -> create_event (freeform parse)
  - "today"                              -> get_today_events
  - "tomorrow"/specific weekday          -> get_events_for_date
  - "upcoming"/"next N days"/default     -> get_upcoming_events
"""

import re
from datetime import datetime, timedelta

import pytz

from tools import calendar_tool

IST = pytz.timezone("Asia/Kolkata")

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


class CalendarAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def _extract_keyword(self, prompt: str, prefixes: list) -> str:
        for p in prefixes:
            m = re.search(rf"{p}\s+(?:the\s+)?(?:event\s+)?(?:for\s+|about\s+|called\s+)?(.+)$", prompt, re.IGNORECASE)
            if m:
                return m.group(1).strip().rstrip(".")
        return ""

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "").strip()
        low = prompt.lower()
        if self.verbose:
            print(f"[calendar_agent] Handling: {prompt[:80]!r}")

        if re.search(r"\bjoin\b.*\bmeet\b|\bjoin\b.*\bcall\b|\bjoin\b.*\bmeeting\b", low):
            return calendar_tool.join_meet()

        if re.search(r"\b(delete|cancel|remove)\b", low):
            keyword = self._extract_keyword(prompt, ["delete", "cancel", "remove"])
            if not keyword:
                return "GAP: tell me which event to delete (e.g. 'cancel the dentist appointment')."
            return calendar_tool.delete_event(keyword)

        if re.search(r"\b(update|reschedule|move|change)\b", low):
            keyword = self._extract_keyword(prompt, ["update", "reschedule", "move", "change"])
            new_time = ""
            time_match = re.search(r"to\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)", low)
            if time_match:
                new_time = time_match.group(1)
            if not keyword:
                return "GAP: tell me which event to update and what should change."
            return calendar_tool.update_event(keyword, new_time=new_time)

        if re.search(r"\b(search|find)\b.*\bevent", low) or (re.search(r"\b(search|find)\b", low) and "calendar" in low):
            keyword = self._extract_keyword(prompt, ["search for", "search", "find"])
            if not keyword:
                return "GAP: tell me what to search for."
            return calendar_tool.search_events(keyword)

        if re.search(r"\b(recurring|every day|every week|every month|repeats?)\b", low):
            title = self._extract_keyword(prompt, ["create", "add", "schedule"]) or "New Event"
            recurrence = "weekly"
            if "daily" in low or "every day" in low:
                recurrence = "daily"
            elif "monthly" in low or "every month" in low:
                recurrence = "monthly"
            date_str = "today"
            if "tomorrow" in low:
                date_str = "tomorrow"
            time_match = re.search(r"at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)", low)
            time_str = time_match.group(1) if time_match else "9am"
            return calendar_tool.create_recurring_event(title, date_str, time_str, recurrence=recurrence)

        if re.search(r"\b(create|add|schedule|set up|book)\b.*\bevent\b|\b(create|add|schedule|set up|book)\b.*\bmeeting\b|\bremind me to\b", low):
            return calendar_tool.create_event(prompt)

        if "today" in low:
            return calendar_tool.get_today_events()

        for i, day in enumerate(_WEEKDAYS):
            if day in low:
                today = datetime.now(IST).date()
                days_ahead = (i - today.weekday()) % 7
                days_ahead = days_ahead if days_ahead != 0 else 7
                target = today + timedelta(days=days_ahead)
                return calendar_tool.get_events_for_date(target)

        if "tomorrow" in low:
            target = datetime.now(IST).date() + timedelta(days=1)
            return calendar_tool.get_events_for_date(target)

        days_match = re.search(r"next\s+(\d+)\s*days?", low)
        if days_match:
            return calendar_tool.get_upcoming_events(days=int(days_match.group(1)))

        if re.search(r"\bupcoming\b|\bthis week\b", low):
            return calendar_tool.get_upcoming_events()

        # Default: show upcoming events (safe, informational default)
        return calendar_tool.get_upcoming_events()
