"""
Android Backend — SHRRI Phase 15
Implements DeviceAPI for Android (Termux).
"""
import subprocess


def _run(cmd: str) -> str:
    try:
        return subprocess.run(cmd, shell=True, capture_output=True,
                              text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


class AndroidBackend:
    """Termux-specific implementations using termux-api."""

    def battery(self) -> dict:
        import json
        out = _run("termux-battery-status 2>/dev/null")
        if out:
            try:
                data = json.loads(out)
                return {"percentage": f"{data.get('percentage', '?')}%",
                        "state": data.get("status", "?"),
                        "source": "termux-api"}
            except Exception:
                pass
        return {"percentage": "unknown", "state": "unknown", "source": "none"}

    def wifi(self) -> dict:
        import json
        out = _run("termux-wifi-connectioninfo 2>/dev/null")
        if out:
            try:
                data = json.loads(out)
                return {"ssid": data.get("ssid", "?"), "ip": data.get("ip", "?")}
            except Exception:
                pass
        return {"ssid": "unknown", "ip": "unknown"}

    def disk(self) -> dict:
        out = _run("df -h /data | tail -1")
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
        return {"load_avg": load, "cores": cores, "model": "ARM (Android)"}

    def screen_brightness(self, level: int = None) -> dict:
        return {"note": "Use termux-brightness via termux-api"}

    def notify(self, title: str, body: str) -> bool:
        _run(f'termux-notification --title "{title}" --content "{body}" 2>/dev/null')
        return True

    def clipboard_get(self) -> str:
        return _run("termux-clipboard-get 2>/dev/null")

    def clipboard_set(self, text: str) -> bool:
        escaped = text.replace("'", "'\\''")
        _run(f"echo '{escaped}' | termux-clipboard-set 2>/dev/null")
        return True

    def open_url(self, url: str) -> bool:
        _run(f"termux-open-url '{url}' 2>/dev/null")
        return True

    def system_info(self) -> dict:
        uptime = _run("uptime -p 2>/dev/null")
        return {"uptime": uptime, "note": "Android/Termux"}
