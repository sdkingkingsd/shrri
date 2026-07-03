"""
Device API — SHRRI Phase 15
Unified interface for device operations across platforms.
"""
import platform
import subprocess
import os
from pathlib import Path


def get_platform() -> str:
    """Detect current platform."""
    system = platform.system().lower()
    if system == "linux":
        # Check if Android (Termux)
        if os.path.exists("/data/data/com.termux") or "android" in platform.version().lower():
            return "android"
        return "linux"
    elif system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    return "unknown"


class DeviceAPI:
    """
    Unified device API — routes calls to the right backend.
    """
    def __init__(self):
        self.platform = get_platform()
        self._backend = self._load_backend()

    def _load_backend(self):
        if self.platform in ("linux", "android"):
            from engine.device_linux import LinuxBackend
            return LinuxBackend()
        # Future: WindowsBackend, MacOSBackend
        from engine.device_linux import LinuxBackend
        return LinuxBackend()  # best fallback for now

    # --- Unified interface ---

    def battery(self) -> dict:
        return self._backend.battery()

    def wifi(self) -> dict:
        return self._backend.wifi()

    def disk(self) -> dict:
        return self._backend.disk()

    def memory(self) -> dict:
        return self._backend.memory()

    def cpu(self) -> dict:
        return self._backend.cpu()

    def screen_brightness(self, level: int = None) -> dict:
        return self._backend.screen_brightness(level)

    def notify(self, title: str, body: str) -> bool:
        return self._backend.notify(title, body)

    def clipboard_get(self) -> str:
        return self._backend.clipboard_get()

    def clipboard_set(self, text: str) -> bool:
        return self._backend.clipboard_set(text)

    def open_url(self, url: str) -> bool:
        return self._backend.open_url(url)

    def system_info(self) -> dict:
        return {
            "platform": self.platform,
            "os": platform.system(),
            "version": platform.version(),
            "machine": platform.machine(),
            "hostname": platform.node(),
            "python": platform.python_version(),
            **self._backend.system_info()
        }
