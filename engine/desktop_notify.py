"""
Desktop Notification — SHRRI Phase 16
Cross-platform desktop notifications using device_api + fallbacks.
"""
import subprocess
import os
from engine.device_api import get_platform


def notify(title: str, body: str, urgency: str = "normal", icon: str = "") -> bool:
    """
    Send a desktop notification. Returns True if sent successfully.
    urgency: low | normal | critical
    """
    platform = get_platform()

    if platform == "android":
        # Termux
        cmd = f'termux-notification --title "{title}" --content "{body}" 2>/dev/null'
        return subprocess.run(cmd, shell=True).returncode == 0

    # Linux — try in order: notify-send, zenity, xmessage
    if _try_notify_send(title, body, urgency, icon):
        return True
    if _try_zenity(title, body):
        return True
    if _try_xmessage(title, body):
        return True

    # Last resort: print to terminal
    print(f"\n🔔 [{urgency.upper()}] {title}: {body}\n")
    return False


def _try_notify_send(title: str, body: str, urgency: str, icon: str) -> bool:
    icon_flag = f'--icon="{icon}"' if icon else ""
    cmd = f'notify-send --urgency={urgency} {icon_flag} "{title}" "{body}" 2>/dev/null'
    try:
        return subprocess.run(cmd, shell=True, timeout=3).returncode == 0
    except Exception:
        return False


def _try_zenity(title: str, body: str) -> bool:
    cmd = f'zenity --notification --text="{title}: {body}" 2>/dev/null'
    try:
        return subprocess.run(cmd, shell=True, timeout=3).returncode == 0
    except Exception:
        return False


def _try_xmessage(title: str, body: str) -> bool:
    cmd = f'xmessage -center "{title}: {body}" 2>/dev/null &'
    try:
        subprocess.run(cmd, shell=True, timeout=1)
        return True
    except Exception:
        return False


def notify_info(title: str, body: str) -> bool:
    return notify(title, body, urgency="normal")


def notify_warn(title: str, body: str) -> bool:
    return notify(title, body, urgency="normal")


def notify_critical(title: str, body: str) -> bool:
    return notify(title, body, urgency="critical")
