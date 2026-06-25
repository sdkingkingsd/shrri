from datetime import datetime

def get_current_time() -> str:
    now = datetime.now()
    return now.strftime("Current time: %I:%M %p, %A, %B %d, %Y")
