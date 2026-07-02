"""
Android Agent — SHRRI AI OS v2 (Phase 5)

Thin wrapper around real `adb` (Android Debug Bridge) commands. No
device is paired as of writing this — that's fine, this agent is built
around the real tool, and honestly reports "no device connected" when
`adb devices` comes back empty, rather than fabricating phone state.

To actually control a device: connect via USB with USB debugging
enabled, or pair over Wi-Fi with `adb pair <ip>:<port>` (Android 11+),
then this agent's commands will work against it live.

Intent routing (checked in order):
  - "devices"/"connected"/"paired"      -> adb devices (list real state)
  - "battery"                            -> adb shell dumpsys battery
  - "screenshot"                         -> adb exec-out screencap, saved to disk
  - "install" + apk path                 -> adb install <path>
  - "uninstall" + package name            -> adb uninstall <package>
  - "apps"/"installed apps"/"list apps"  -> adb shell pm list packages
  - "notification"/"notify"              -> adb shell cmd notification post
  - everything else                      -> explain available commands
"""

import re
import subprocess
import time


def _run_adb(args: list, timeout: int = 15) -> tuple:
    try:
        result = subprocess.run(
            ["adb"] + args, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, (result.stdout or "") + (result.stderr or "")
    except FileNotFoundError:
        return -1, "adb is not installed on this machine."
    except subprocess.TimeoutExpired:
        return -1, "adb command timed out."


def _parse_device_lines(out: str) -> list:
    """Only real device entries — skip daemon-startup noise and the
    'List of devices attached' header."""
    lines = out.strip().splitlines()
    devices = []
    for l in lines:
        l = l.strip()
        if not l or "List of devices attached" in l or l.startswith("*") or l.startswith("daemon"):
            continue
        if "\t" in l or re.search(r"\s+(device|unauthorized|offline)$", l):
            devices.append(l)
    return devices


def _has_device() -> bool:
    code, out = _run_adb(["devices"])
    if code != 0:
        return False
    return len(_parse_device_lines(out)) > 0


class AndroidAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "").strip()
        low = prompt.lower()
        if self.verbose:
            print(f"[android_agent] Handling: {prompt[:80]!r}")

        # List connected/paired devices (always safe, no device required)
        if re.search(r"\b(device|connected|paired)\b", low):
            code, out = _run_adb(["devices"])
            devices = _parse_device_lines(out)
            if not devices:
                return (
                    "No Android device connected. Pair one via USB (enable USB "
                    "debugging in Developer Options) or wirelessly with "
                    "'adb pair <ip>:<port>' (Android 11+), then try again."
                )
            return "Connected devices:\n" + "\n".join(devices)

        # Everything below requires a real paired device — check first,
        # report honestly instead of guessing at phone state.
        if not _has_device():
            return (
                "No Android device is currently connected, so I can't do that. "
                "Connect via USB with debugging enabled, or pair over Wi-Fi "
                "with 'adb pair <ip>:<port>', then try again."
            )

        if "battery" in low:
            code, out = _run_adb(["shell", "dumpsys", "battery"])
            return out.strip() or "Could not read battery status."

        if "screenshot" in low:
            device_path = "/sdcard/shrri_screenshot.png"
            local_path = f"/home/shrridharshan/shrri_screenshot_{int(time.time())}.png"
            code, out = _run_adb(["shell", "screencap", "-p", device_path])
            if code != 0:
                return f"Screenshot failed: {out}"
            code2, out2 = _run_adb(["pull", device_path, local_path])
            if code2 != 0:
                return f"Screenshot captured on device but pull failed: {out2}"
            return f"Screenshot saved to {local_path}"

        install_match = re.search(r"install\s+(\S+\.apk)", prompt, re.IGNORECASE)
        if install_match:
            apk_path = install_match.group(1)
            code, out = _run_adb(["install", apk_path], timeout=60)
            return out.strip() or ("Installed." if code == 0 else "Install failed.")

        uninstall_match = re.search(r"uninstall\s+([\w.]+)", prompt, re.IGNORECASE)
        if uninstall_match:
            package = uninstall_match.group(1)
            code, out = _run_adb(["uninstall", package])
            return out.strip() or ("Uninstalled." if code == 0 else "Uninstall failed.")

        if re.search(r"\b(apps|packages)\b", low):
            code, out = _run_adb(["shell", "pm", "list", "packages"])
            packages = out.strip().splitlines()
            return f"{len(packages)} installed packages:\n" + "\n".join(packages[:40])

        return (
            "I can check connected devices, read battery status, take a "
            "screenshot, install/uninstall an APK, or list installed apps "
            "on a paired Android device via adb — say which one you want."
        )
