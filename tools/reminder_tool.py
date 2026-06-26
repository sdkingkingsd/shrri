"""Reminder tool — schedules desktop notifications via cron."""
import re
import subprocess
from datetime import datetime, timedelta
import pytz

IST = pytz.timezone("Asia/Kolkata")

def _parse_time(text: str):
    """Parse time from natural language. Returns (hour, minute) or None."""
    text = text.lower().strip()
    # "at 6pm", "at 6:30pm", "at 18:00"
    # Handle "950am" or "950 am" as 9:50 am
    text = re.sub(r'at\s+(\d)(\d{2})\s*(am|pm)', r'at \1:\2 \3', text)
    text = re.sub(r'at\s+(\d{2})(\d{2})\s*(am|pm)', r'at \1:\2 \3', text)
    m = re.search(r'at\s+(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)?', text)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        period = m.group(3)
        if period == 'pm' and hour != 12:
            hour += 12
        if period == 'am' and hour == 12:
            hour = 0
        return hour, minute
    # "in X minutes"
    m2 = re.search(r'in\s+(\d+)\s+minutes?', text)
    if m2:
        future = datetime.now(IST) + timedelta(minutes=int(m2.group(1)))
        return future.hour, future.minute
    # "in X hours"
    m3 = re.search(r'in\s+(\d+)\s+hours?', text)
    if m3:
        future = datetime.now(IST) + timedelta(hours=int(m3.group(1)))
        return future.hour, future.minute
    return None

def _parse_task(text: str) -> str:
    """Extract the task from the reminder message."""
    text = text.lower()
    for marker in ["to remind me to", "remind me to", "to ", "that "]:
        idx = text.find(marker)
        if idx != -1:
            return text[idx + len(marker):].strip()
    return text.strip()

def set_reminder(message: str) -> str:
    """Parse and schedule a reminder."""
    try:
        time_result = _parse_time(message)
        if not time_result:
            return "GAP: couldn't understand the time. Try 'remind me at 6pm to call mom' or 'remind me in 30 minutes to drink water'."
        
        hour, minute = time_result
        task = _parse_task(message)
        if not task:
            task = "Reminder from SHRRI"

        # Build cron job: runs notify-send at specified time
        cron_cmd = f'{minute} {hour} * * * DISPLAY=:0 /usr/bin/notify-send "SHRRI Reminder" "{task}" 2>/dev/null'
        
        # Add to crontab
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        existing = result.stdout if result.returncode == 0 else ''
        
        # Avoid duplicate reminders
        new_crontab = existing.rstrip() + '\n' + cron_cmd + '\n'
        subprocess.run(['crontab', '-'], input=new_crontab, text=True, check=True)

        now = datetime.now(IST)
        remind_time = now.replace(hour=hour, minute=minute, second=0)
        if remind_time < now:
            remind_time += timedelta(days=1)
        
        time_str = remind_time.strftime("%I:%M %p")
        return f"⏰ Reminder set for {time_str} — I'll notify you to: {task}"

    except Exception as e:
        return f"GAP: reminder failed — {e}"

def list_reminders() -> str:
    """Show all scheduled reminders."""
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode != 0 or not result.stdout.strip():
            return "No reminders set."
        lines = [l for l in result.stdout.strip().split('\n') if 'notify-send' in l and 'SHRRI Reminder' in l]
        if not lines:
            return "No reminders set."
        out = ["⏰ Active reminders:"]
        for l in lines:
            m = re.search(r'(\d+)\s+(\d+)\s+\*.*notify-send.*"SHRRI Reminder"\s+"([^"]+)"', l)
            if m:
                h, mi, task = int(m.group(2)), int(m.group(1)), m.group(3)
                t = datetime.now(IST).replace(hour=h, minute=mi).strftime("%I:%M %p")
                out.append(f"  • {t} — {task}")
        return "\n".join(out)
    except Exception as e:
        return f"GAP: {e}"
