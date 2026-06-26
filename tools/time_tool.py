from datetime import datetime

def get_current_time() -> str:
    now = datetime.now()
    return now.strftime("Current time: %I:%M %p, %A, %B %d, %Y")


def get_current_date() -> str:
    from datetime import datetime
    now = datetime.now()
    return now.strftime("Today's date: %A, %B %d, %Y")
