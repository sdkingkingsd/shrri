"""
Linux Backend — SHRRI Phase 15
Implements DeviceAPI for Linux (and Android/Termux).
"""
import subprocess
import os
import shutil
from pathlib import Path


def _run(cmd: str, timeout: int = 5) -> str:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True,
                                text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception:
        return ""


class LinuxBackend:

    def battery(self) -> dict:
        # Try upower
        out = _run("upower -i $(upower -e | grep battery) 2>/dev/null | grep -E 'percentage|state|time'")
        if out:
            lines = {l.split(":")[0].strip(): l.split(":")[1].strip()
                     for l in out.splitlines() if ":" in l}
            return {"percentage": lines.get("percentage", "?"),
                    "state": lines.get("state", "?"),
                    "source": "upower"}
        # Try /sys
        try:
            cap = Path("/sys/class/power_supply/BAT0/capacity").read_text().strip()
            status = Path("/sys/class/power_supply/BAT0/status").read_text().strip()
            return {"percentage": f"{cap}%", "state": status, "source": "sysfs"}
        except Exception:
            return {"percentage": "unknown", "state": "unknown", "source": "none"}

    def wifi(self) -> dict:
        ssid = _run("iwgetid -r 2>/dev/null || nmcli -t -f active,ssid dev wifi 2>/dev/null | grep '^yes' | cut -d: -f2")
        ip = _run("hostname -I 2>/dev/null | awk '{print $1}'")
        return {"ssid": ssid or "unknown", "ip": ip or "unknown"}

    def disk(self) -> dict:
        out = _run("df -h / | tail -1")
        if out:
            parts = out.split()
            return {"total": parts[1], "used": parts[2], "free": parts[3], "use_pct": parts[4]}
        return {}

    def memory(self) -> dict:
        out = _run("free -h | grep Mem:")
        if out:
            parts = out.split()
            return {"total": parts[1], "used": parts[2], "free": parts[3]}
        return {}

    def cpu(self) -> dict:
        load = _run("cat /proc/loadavg | awk '{print $1,$2,$3}'")
        cores = _run("nproc")
        model = _run("grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2").strip()
        return {"load_avg": load, "cores": cores, "model": model or "unknown"}

    def screen_brightness(self, level: int = None) -> dict:
        if level is not None:
            _run(f"brightnessctl set {level}% 2>/dev/null || xbacklight -set {level} 2>/dev/null")
            return {"set": level}
        current = _run("brightnessctl get 2>/dev/null || xbacklight -get 2>/dev/null")
        return {"current": current or "unknown"}

    def notify(self, title: str, body: str) -> bool:
        result = _run(f'notify-send "{title}" "{body}" 2>/dev/null')
        return True  # best effort

    def clipboard_get(self) -> str:
        return _run("xclip -o -selection clipboard 2>/dev/null || xsel --clipboard --output 2>/dev/null")

    def clipboard_set(self, text: str) -> bool:
        escaped = text.replace("'", "'\\''")
        _run(f"echo '{escaped}' | xclip -selection clipboard 2>/dev/null || echo '{escaped}' | xsel --clipboard --input 2>/dev/null")
        return True

    def open_url(self, url: str) -> bool:
        _run(f"xdg-open '{url}' 2>/dev/null &")
        return True

    def system_info(self) -> dict:
        uptime = _run("uptime -p 2>/dev/null")
        return {"uptime": uptime or "unknown"}
