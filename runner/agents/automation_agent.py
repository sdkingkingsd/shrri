"""
Automation Agent — SHRRI AI OS v2 (Phase 5)

Thin wrapper around the existing tools.reminder_tool and tools.scheduler
modules, which already do the real work (cron/at job creation, Telegram
delivery, crontab parsing for gmail/whatsapp/weather/briefing automations).

This agent's job is just intent routing: given a natural-language
automation request, decide which existing function handles it and call
it directly — no new scheduling mechanism is introduced here.

Intent routing (checked in order):
  - "list" + reminder/automation word     -> list existing (reminders + schedules)
  - "delete"/"cancel"/"remove" + keyword  -> delete matching reminder/schedule
  - "remind me ..."                       -> reminder_tool.set_reminder
  - everything else (recurring automation like "every morning briefing",
    "check gmail every hour")             -> scheduler.add_schedule
"""

import re

from tools import reminder_tool
from tools import scheduler as automation_scheduler


class AutomationAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "").strip()
        low = prompt.lower()
        if self.verbose:
            print(f"[automation_agent] Handling: {prompt[:80]!r}")

        # LIST
        if re.search(r"\b(list|show|what)\b.*\b(remind|automat|schedul)", low):
            reminders = reminder_tool.list_reminders()
            schedules = automation_scheduler.list_schedules()
            return f"{reminders}\n\n{schedules}"

        # DELETE / CANCEL
        del_match = re.search(
            r"\b(delete|cancel|remove|stop)\b(?:\s+(?:all\s+)?(?:the\s+)?(?:reminder|automation)s?)?\s*(?:for|to|about)?\s*(.*)$",
            low,
        )
        if del_match:
            if "all" in low:
                return reminder_tool.delete_all_reminders()
            keyword = del_match.group(2).strip()
            if keyword:
                result = reminder_tool.delete_reminder(keyword)
                if result.startswith("No reminder found"):
                    # Fall back to schedule deletion by the same keyword
                    return automation_scheduler.delete_schedule(keyword)
                return result
            return "GAP: tell me which reminder or automation to delete (e.g. 'delete reminder to call mom')."

        # REMIND ME (one-shot or recurring reminder)
        if "remind me" in low or low.startswith("remind "):
            return reminder_tool.set_reminder(prompt)

        # Default: recurring automation (briefings, gmail/whatsapp/weather checks)
        result = automation_scheduler.add_schedule(prompt)
        if result.startswith("GAP:"):
            # Last-resort fallback — maybe it was actually a reminder-shaped
            # request that didn't say "remind me" explicitly.
            fallback = reminder_tool.set_reminder(prompt)
            if not fallback.startswith("GAP:"):
                return fallback
        return result
