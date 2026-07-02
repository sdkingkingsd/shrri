"""System control tool — lock, shutdown, restart, volume, brightness."""
import subprocess
import re

def system_control(message: str) -> str:
    msg = message.lower()
    try:
        # Lock screen
        if any(t in msg for t in ["lock screen", "lock my screen", "lock computer"]):
            # Try multiple lock methods
            for cmd in [["xdg-screensaver", "lock"],
                        ["gnome-screensaver-command", "-l"],
                        ["loginctl", "lock-session"],
                        ["xlock"],
                        ["dm-tool", "lock"]]:
                try:
                    subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
                    return "🔒 Screen locked."
                except FileNotFoundError:
                    continue
            return "GAP: no screen lock tool found."

        # Shutdown
        m = re.search(r"shutdown\s+in\s+(\d+)\s*(minutes?|mins?|hours?)?", msg)
        if m:
            mins = int(m.group(1))
            if m.group(2) and "hour" in m.group(2):
                mins *= 60
            subprocess.run(["shutdown", "-h", f"+{mins}"], check=True)
            return f"⏻ Shutdown scheduled in {mins} minutes."
        if any(t in msg for t in ["shutdown now", "shut down now", "power off"]):
            subprocess.run(["shutdown", "-h", "now"])
            return "⏻ Shutting down..."

        # Restart
        if any(t in msg for t in ["restart now", "reboot now"]):
            subprocess.run(["reboot"])
            return "🔄 Restarting..."
        m2 = re.search(r"restart\s+in\s+(\d+)\s*(minutes?|mins?)?", msg)
        if m2:
            mins = int(m2.group(1))
            subprocess.run(["shutdown", "-r", f"+{mins}"])
            return f"🔄 Restart scheduled in {mins} minutes."

        # Cancel shutdown
        if any(t in msg for t in ["cancel shutdown", "cancel restart"]):
            subprocess.run(["shutdown", "-c"])
            return "✅ Shutdown/restart cancelled."

        # Volume
        m3 = re.search(r"volume\s+(?:to|at)?\s*(\d+)", msg)
        if m3:
            vol = min(100, int(m3.group(1)))
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{vol}%"])
            return f"🔊 Volume set to {vol}%."
        if "mute" in msg:
            subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])
            return "🔇 Volume toggled mute."
        if "volume up" in msg:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"])
            return "🔊 Volume increased."
        if "volume down" in msg:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"])
            return "🔉 Volume decreased."

        # Brightness
        m4 = re.search(r"brightness\s+(?:to|at)?\s*(\d+)", msg)
        if m4:
            val = min(100, int(m4.group(1)))
            subprocess.run(["brightnessctl", "set", f"{val}%"],
                           capture_output=True)
            return f"☀️ Brightness set to {val}%."
        if "brightness up" in msg:
            subprocess.run(["brightnessctl", "set", "10%+"], capture_output=True)
            return "☀️ Brightness increased."
        if "brightness down" in msg:
            subprocess.run(["brightnessctl", "set", "10%-"], capture_output=True)
            return "🌙 Brightness decreased."

        return "GAP: unknown system command."
    except Exception as e:
        return f"GAP: system command failed — {e}"
