"""Daily briefing — weather + emails + calendar in one shot."""

def get_briefing() -> str:
    from datetime import datetime
    import pytz
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz)
    greeting = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 17 else "Good evening"

    lines = [f"{greeting}, Shrridharshan! Here's your briefing for {now.strftime('%A, %B %d')}:\n"]

    # Weather
    try:
        from tools.weather_tool import get_weather
        lines.append(get_weather("Chennai"))
    except Exception as e:
        lines.append(f"Weather: unavailable ({e})")

    lines.append("")

    # Calendar
    try:
        from tools.calendar_tool import get_today_events
        lines.append(get_today_events())
    except Exception as e:
        lines.append(f"Calendar: unavailable ({e})")

    lines.append("")

    # Emails
    try:
        from tools.gmail import read_emails
        emails = read_emails(max_results=3, query="is:unread")
        if emails:
            lines.append("📬 Latest emails:\n" + str(emails))
        else:
            lines.append("📬 No unread emails.")
    except Exception as e:
        lines.append(f"Email: unavailable ({e})")

    return "\n".join(lines)
