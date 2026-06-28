"""run_automation.py — called by cron to execute scheduled SHRRI tasks."""
import sys
import os
sys.path.insert(0, os.path.expanduser("~/shrri"))

def run(task_type, task_action, label):
    from tools.voice_tool import speak
    result = ""

    if task_action == "morning_briefing":
        from tools.weather_tool import get_weather
        from tools.gmail import read_gmail
        from tools.briefing_tool import get_briefing
        weather = get_weather("Salem")
        briefing = get_briefing()
        result = f"வணக்கம் ஷ்ரிதர்ஷன். {weather}. {briefing}"

    elif task_action == "check_gmail":
        from tools.gmail import read_gmail
        result = read_gmail()
        result = "உங்க Gmail summary: " + result[:200]

    elif task_action == "check_weather":
        from tools.weather_tool import get_weather
        result = get_weather("Salem")

    elif task_action == "check_whatsapp":
        from tools.whatsapp_reader import read_whatsapp
        result = read_whatsapp()
        result = "WhatsApp update: " + result[:200]

    elif task_action == "drink_water":
        result = "ஷ்ரிதர்ஷன், தண்ணீர் குடிக்கணும். Stay hydrated!"

    elif task_action == "night_summary":
        from engine.memory import Memory
        m = Memory()
        count = m.conn.execute("SELECT COUNT(*) FROM conversations WHERE timestamp > date('now')").fetchone()[0]
        result = f"இன்னிக்கு summary: {count} conversations had today. Good night ஷ்ரிதர்ஷன்!"

    else:
        result = f"SHRRI automation: {label}"

    if result:
        print(f"[{label}] {result[:100]}")
        try:
            speak(result[:300])
        except Exception as e:
            print(f"Speak error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: run_automation.py <task_type> <task_action> <label>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2], sys.argv[3])