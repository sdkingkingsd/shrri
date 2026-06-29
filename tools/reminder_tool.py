"""Reminder tool — schedules desktop notifications via cron (recurring) or at (one-shot)."""
import re
import subprocess
from datetime import datetime, timedelta
import pytz
import dateparser

IST = pytz.timezone("Asia/Kolkata")

RECURRING_KEYWORDS = ["every day", "everyday", "daily", "every morning", "every night", "every week", "weekly", "every month", "monthly", "every monday", "every tuesday", "every wednesday", "every thursday", "every friday", "every saturday", "every sunday"]


def _is_recurring(text: str) -> bool:
    text = text.lower()
    return any(kw in text for kw in RECURRING_KEYWORDS)


def _normalize_bare_hour(text: str) -> str:
    """
    'tomorrow 9am' -> 'tomorrow 9:00am'
    Works around a dateparser quirk where a bare "<hour>am/pm" (no colon)
    combined with a relative-day word like "tomorrow" silently drops the
    hour and falls back to the current time-of-day. Already-colon'd times
    (e.g. "9:30am") are left untouched.
    """
    return re.sub(r'\b(\d{1,2})\s*(am|pm)\b', r'\1:00\2', text, flags=re.IGNORECASE)


def _date_search_settings(now: datetime) -> dict:
    return {
        "TIMEZONE": "Asia/Kolkata",
        "TO_TIMEZONE": "Asia/Kolkata",
        "RETURN_AS_TIMEZONE_AWARE": True,
        "RELATIVE_BASE": now.replace(tzinfo=None),
        "PREFER_DATES_FROM": "future",
    }


def _find_date_phrase(text: str, now: datetime):
    """
    Returns (matched_phrase, parsed_datetime) for the date/time expression
    found in text, or (None, None) if nothing parseable was found.
    """
    from dateparser.search import search_dates

    normalized = _normalize_bare_hour(text)
    results = search_dates(normalized, settings=_date_search_settings(now), languages=["en"])
    if not results:
        return None, None

    phrase, parsed = results[-1]

    if parsed.tzinfo is None:
        parsed = IST.localize(parsed)

    return phrase, parsed


def _parse_datetime(text: str):
    """
    Parse a date+time from natural language using dateparser.
    Handles: 'tomorrow 9am', 'tonight 8pm', 'next monday 5pm',
             'in 30 minutes', 'at 6pm', 'in 2 hours', etc.
    Returns a timezone-aware datetime in IST, or None if nothing parseable found.
    """
    now = datetime.now(IST)
    _, parsed = _find_date_phrase(text, now)
    if parsed is None:
        return None

    lowered = text.lower()
    if parsed < now and "tomorrow" not in lowered and "next" not in lowered:
        parsed = parsed + timedelta(days=1)

    return parsed


def _parse_weekday(text: str):
    """Return weekday index (0=Mon..6=Sun) if found."""
    # cron weekday: 0=Sun,1=Mon,2=Tue,3=Wed,4=Thu,5=Fri,6=Sat
    days = {"monday":1,"tuesday":2,"wednesday":3,"thursday":4,"friday":5,"saturday":6,"sunday":0}
    text = text.lower()
    for d, idx in days.items():
        if d in text:
            return idx
    return None

def _parse_monthly_day(text: str):
    """Return day of month if found."""
    m = re.search(r"every\s+(\d{1,2})(?:st|nd|rd|th)?\s+of", text.lower())
    if m:
        return int(m.group(1))
    m = re.search(r"monthly\s+on\s+(?:the\s+)?(\d{1,2})", text.lower())
    if m:
        return int(m.group(1))
    return None

def _parse_recurring_time(text: str):
    """
    Parse just the time-of-day for recurring reminders like 'every day at 5am'.
    dateparser's search_dates doesn't recognize recurrence phrases ('every day
    at X') as date expressions, so this uses a focused regex instead.
    Returns (hour, minute) or None.
    """
    normalized = _normalize_bare_hour(text)
    m = re.search(r'at\s+(\d{1,2})[:.](\d{2})\s*(am|pm)?', normalized, re.IGNORECASE)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2))
    period = (m.group(3) or "").lower()
    if period == 'pm' and hour != 12:
        hour += 12
    if period == 'am' and hour == 12:
        hour = 0
    return hour, minute


def _parse_task(text: str) -> str:
    """Extract the task from the reminder message, with the date/time phrase removed."""
    now = datetime.now(IST)
    original = text

    task = original
    marker_patterns = [
        r'\bto remind me to\b',
        r'\bremind me to\b',
        r'\bto\b',
        r'\bthat\b',
    ]
    for pattern in marker_patterns:
        m = re.search(pattern, original, re.IGNORECASE)
        if m:
            task = original[m.end():].strip()
            break

    phrase, _ = _find_date_phrase(task, now)
    if phrase:
        normalized_task = _normalize_bare_hour(task)
        normalized_task = re.sub(r'\b' + re.escape(phrase) + r'\b', "", normalized_task, flags=re.IGNORECASE)
        task = re.sub(r'\s{2,}', ' ', normalized_task).strip(" ,.-")

    task = re.sub(r'\b(every day|everyday|daily|every morning|every night)\b', '', task, flags=re.IGNORECASE)
    task = re.sub(r'\s{2,}', ' ', task).strip(" ,.-")

    return task or "Reminder from SHRRI"


def _schedule_recurring(hour: int, minute: int, task: str, freq: str = "daily", weekday: int = None, day: int = None) -> str:
    """Crontab-based reminder with Telegram delivery."""
    notify_cmd = f'python3 /home/shrridharshan/shrri/tools/telegram_notify.py "⏰ SHRRI Reminder: {task}"'
    if freq == "weekly" and weekday is not None:
        cron_expr = f"{minute} {hour} * * {weekday}"
        _cron_day_names = {0:'Sun',1:'Mon',2:'Tue',3:'Wed',4:'Thu',5:'Fri',6:'Sat'}
        human = f"weekly on {_cron_day_names.get(weekday,'Mon')} at {hour:02d}:{minute:02d}"
    elif freq == "monthly" and day is not None:
        cron_expr = f"{minute} {hour} {day} * *"
        human = f"monthly on day {day} at {hour:02d}:{minute:02d}"
    else:
        cron_expr = f"{minute} {hour} * * *"
        human = f"daily at {hour:02d}:{minute:02d}"
    cron_cmd = f"{cron_expr} {notify_cmd}"
    result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ''
    new_crontab = existing.rstrip() + '\n' + cron_cmd + '\n'
    subprocess.run(['crontab', '-'], input=new_crontab, text=True, check=True)
    return f"⏰ Reminder set ({human}) — I'll message you on Telegram to: {task}"


def _schedule_oneshot(remind_time: datetime, task: str) -> str:
    """One-shot reminder via at — sends Telegram message."""
    at_time_str = remind_time.strftime("%H:%M %Y-%m-%d")
    notify_cmd = f'python3 /home/shrridharshan/shrri/tools/telegram_notify.py "⏰ SHRRI Reminder: {task}"'
    proc = subprocess.run(
        ['at', at_time_str],
        input=notify_cmd,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "`at` scheduling failed")
    time_str = remind_time.strftime("%I:%M %p on %d %b %Y")
    return f"⏰ Reminder set for {time_str} — I'll message you on Telegram to: {task}"


def set_reminder(message: str) -> str:
    """Parse and schedule a reminder (recurring via cron, or one-shot via at)."""
    try:
        task = _parse_task(message)

        if _is_recurring(message):
            time_result = _parse_recurring_time(message)
            if not time_result:
                return ("GAP: couldn't understand the time for the recurring reminder. "
                        "Try 'remind me every day at 6pm to call mom'.")
            hour, minute = time_result
            msg_lower = message.lower()
            if any(w in msg_lower for w in ["every week","weekly","every monday","every tuesday","every wednesday","every thursday","every friday","every saturday","every sunday"]):
                weekday = _parse_weekday(message)
                return _schedule_recurring(hour, minute, task, freq="weekly", weekday=weekday if weekday is not None else 0)
            elif any(w in msg_lower for w in ["every month","monthly"]):
                day = _parse_monthly_day(message) or 1
                return _schedule_recurring(hour, minute, task, freq="monthly", day=day)
            else:
                return _schedule_recurring(hour, minute, task, freq="daily")

        remind_dt = _parse_datetime(message)
        if not remind_dt:
            return ("GAP: couldn't understand the time. Try 'remind me at 6pm to call mom', "
                    "'remind me tomorrow 9am to call mom', or 'remind me in 30 minutes to drink water'.")
        return _schedule_oneshot(remind_dt, task)

    except Exception as e:
        return f"GAP: reminder failed — {e}"



def delete_reminder(keyword: str) -> str:
    """Delete a specific reminder matching keyword."""
    try:
        deleted = []
        # Check cron
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            kept = []
            for l in lines:
                if 'SHRRI Reminder' in l and keyword.lower() in l.lower():
                    deleted.append("cron: " + l[:60])
                else:
                    kept.append(l)
            if deleted:
                subprocess.run(['crontab', '-'], input='\n'.join(kept) + '\n', text=True, check=True)
        # Check at jobs
        atq = subprocess.run(['atq'], capture_output=True, text=True)
        if atq.returncode == 0 and atq.stdout.strip():
            for line in atq.stdout.strip().split('\n'):
                parts = line.split('\t') if '\t' in line else line.split()
                job_id = parts[0]
                cat_result = subprocess.run(['at', '-c', job_id], capture_output=True, text=True)
                if 'SHRRI Reminder' in cat_result.stdout and keyword.lower() in cat_result.stdout.lower():
                    subprocess.run(['atrm', job_id], capture_output=True)
                    deleted.append(f"at job {job_id}")
        if not deleted:
            return f"No reminder found matching '{keyword}'."
        return f"✅ Deleted {len(deleted)} reminder(s) matching '{keyword}'."
    except Exception as e:
        return f"GAP: {e}"

def delete_all_reminders() -> str:
    """Delete all SHRRI reminders — both cron (daily) and at (one-shot)."""
    try:
        deleted = []
        # Remove cron entries
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            kept = [l for l in lines if not ('notify-send' in l and 'SHRRI Reminder' in l)]
            removed = len(lines) - len(kept)
            new_crontab = '\n'.join(kept) + '\n'
            subprocess.run(['crontab', '-'], input=new_crontab, text=True, check=True)
            if removed:
                deleted.append(f"{removed} daily reminder(s)")
        # Remove at jobs
        atq = subprocess.run(['atq'], capture_output=True, text=True)
        if atq.returncode == 0 and atq.stdout.strip():
            count = 0
            for line in atq.stdout.strip().split('\n'):
                parts = line.split('\t') if '\t' in line else line.split()
                job_id = parts[0]
                cat_result = subprocess.run(['at', '-c', job_id], capture_output=True, text=True)
                if 'SHRRI Reminder' in cat_result.stdout:
                    subprocess.run(['atrm', job_id], capture_output=True)
                    count += 1
            if count:
                deleted.append(f"{count} one-shot reminder(s)")
        if not deleted:
            return "No reminders to delete."
        return "✅ Deleted: " + ", ".join(deleted) + "."
    except Exception as e:
        return f"GAP: {e}"

def list_reminders() -> str:
    """Show all scheduled reminders — both recurring (cron) and one-shot (at)."""
    try:
        out_lines = []

        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            lines = [l for l in result.stdout.strip().split('\n') if 'SHRRI Reminder' in l or ('telegram_notify' in l and 'Reminder' in l)]
            for l in lines:
                # Try telegram_notify pattern first
                tm = re.search(r'(\d+)\s+(\d+)\s+\*\s+\*\s+(\S+).*telegram_notify\.py.*Reminder:\s*([^"]+)"', l)
                if tm:
                    mi, h, wd, task = int(tm.group(1)), int(tm.group(2)), tm.group(3), tm.group(4).strip()
                    t = datetime.now(IST).replace(hour=h, minute=mi).strftime("%I:%M %p")
                    _dn = {'0':'Sun','1':'Mon','2':'Tue','3':'Wed','4':'Thu','5':'Fri','6':'Sat','*':'daily'}
                    freq = "daily" if wd == "*" else f"every {_dn.get(wd, wd)}"
                    out_lines.append(f"  • {t} ({freq}) — {task}")
                    continue
                m = re.search(r'(\d+)\s+(\d+)\s+\*.*notify-send.*"SHRRI Reminder"\s+"([^"]+)"', l)
                if m:
                    h, mi, task = int(m.group(2)), int(m.group(1)), m.group(3)
                    t = datetime.now(IST).replace(hour=h, minute=mi).strftime("%I:%M %p")
                    out_lines.append(f"  • {t} (daily) — {task}")

        atq = subprocess.run(['atq'], capture_output=True, text=True)
        if atq.returncode == 0 and atq.stdout.strip():
            for line in atq.stdout.strip().split('\n'):
                parts = line.split('\t') if '\t' in line else line.split()
                job_id = parts[0]
                cat_result = subprocess.run(['at', '-c', job_id], capture_output=True, text=True)
                task_match = re.search(r'notify-send\s+"SHRRI Reminder"\s+"([^"]+)"', cat_result.stdout)
                task = task_match.group(1) if task_match else "Reminder"
                m = re.match(r'^\S+\s+(\w{3}\s+\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2}\s+\d{4})', line)
                when = m.group(1) if m else line
                out_lines.append(f"  • {when} (once) — {task}")

        if not out_lines:
            return "No reminders set."
        return "⏰ Active reminders:\n" + "\n".join(out_lines)

    except Exception as e:
        return f"GAP: {e}"
