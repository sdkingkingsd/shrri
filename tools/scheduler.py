"""Scheduler tool — recurring automated tasks for SHRRI."""
import re
import subprocess
import json
import os
from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")
SCHEDULE_FILE = os.path.expanduser("~/.shrri/schedules.json")
SHRRI_PATH = os.path.expanduser("~/shrri")

def _load_schedules():
    if os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE) as f:
            return json.load(f)
    return []

def _save_schedules(schedules):
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(schedules, f, indent=2)

def _parse_schedule(text):
    """Parse natural language schedule into cron expression."""
    text = text.lower()
    # Every day at X
    m = re.search(r"every day at (\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
    if m:
        h = int(m.group(1))
        mi = int(m.group(2)) if m.group(2) else 0
        period = m.group(3)
        if period == "pm" and h != 12: h += 12
        if period == "am" and h == 12: h = 0
        return f"{mi} {h} * * *", f"daily at {m.group(1)}:{str(mi).zfill(2)}{period or ""}"
    # Every morning
    if "every morning" in text or "morning briefing" in text:
        return "0 7 * * *", "every morning at 7:00 AM"
    # Every night
    if "every night" in text or "nightly" in text or "night summary" in text:
        return "0 22 * * *", "every night at 10:00 PM"
    # Every hour
    if "every hour" in text or "hourly" in text:
        return "0 * * * *", "every hour"
    # Every X hours
    m2 = re.search(r"every (\d+) hours?", text)
    if m2:
        h = int(m2.group(1))
        return f"0 */{h} * * *", f"every {h} hours"
    # Every week / weekly
    if "every week" in text or "weekly" in text or "every sunday" in text:
        return "0 9 * * 0", "every Sunday at 9:00 AM"
    # Every X minutes
    m3 = re.search(r"every (\d+) minutes?", text)
    if m3:
        mi = int(m3.group(1))
        return f"*/{mi} * * * *", f"every {mi} minutes"
    return None, None

def _detect_task_type(text):
    """Detect what kind of automation task is requested."""
    text = text.lower()
    if any(w in text for w in ["gmail", "email", "mail", "inbox"]):
        return "gmail", "check_gmail"
    if any(w in text for w in ["whatsapp", "whats app", "messages"]):
        return "whatsapp", "check_whatsapp"
    if any(w in text for w in ["weather", "temperature", "rain"]):
        return "weather", "check_weather"
    if any(w in text for w in ["morning briefing", "morning brief", "good morning", "morning summary"]):
        return "briefing", "morning_briefing"
    if any(w in text for w in ["night summary", "daily summary", "end of day", "evening"]):
        return "briefing", "night_summary"
    if any(w in text for w in ["water", "drink"]):
        return "reminder", "drink_water"
    return "general", "notify"

def _build_cron_command(task_type, task_action, label):
    """Build the actual cron command that runs the automation."""
    script = os.path.join(SHRRI_PATH, "tools", "run_automation.py")
    log = os.path.expanduser("~/.shrri/automation.log")
    return f'cd {SHRRI_PATH} && python3 {script} "{task_type}" "{task_action}" "{label}" >> {log} 2>&1'

def add_schedule(message):
    """Add a new scheduled automation."""
    cron_expr, human_time = _parse_schedule(message)
    if not cron_expr:
        return "GAP: couldn't understand the schedule. Try 'every day at 7 AM gmail briefing' or 'every morning briefing'."
    task_type, task_action = _detect_task_type(message)
    label = task_type + " " + task_action.replace("_", " ")
    cron_cmd = _build_cron_command(task_type, task_action, label)
    full_cron = f"{cron_expr} {cron_cmd}"
    # Add to crontab
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""
    if cron_cmd in existing:
        return f"⚙️ Already scheduled: {label} {human_time}"
    new_crontab = existing.rstrip() + "\n" + full_cron + "\n"
    subprocess.run(["crontab", "-"], input=new_crontab, text=True, check=True)
    # Save to schedules.json
    schedules = _load_schedules()
    schedules.append({
        "label": label,
        "cron": cron_expr,
        "task_type": task_type,
        "task_action": task_action,
        "human_time": human_time,
        "created": datetime.now(IST).isoformat()
    })
    _save_schedules(schedules)
    return f"✅ Scheduled: {label} — {human_time}"

def list_schedules():
    """List all scheduled automations."""
    schedules = _load_schedules()
    if not schedules:
        return "No automations scheduled."
    out = ["⚙️ Active automations:"]
    for s in schedules:
        out.append(f"  • {s['label']} — {s['human_time']}")
    return "\n".join(out)

def delete_schedule(label):
    """Delete a scheduled automation by label."""
    schedules = _load_schedules()
    schedules = [s for s in schedules if label.lower() not in s["label"].lower()]
    _save_schedules(schedules)
    # Rebuild crontab without this job
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""
    new_lines = [l for l in existing.splitlines() if label.lower() not in l.lower()]
    subprocess.run(["crontab", "-"], input="\n".join(new_lines) + "\n", text=True)
    return f"✅ Deleted automation: {label}"