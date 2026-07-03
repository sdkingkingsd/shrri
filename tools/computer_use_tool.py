"""
Computer Use Tool — SHRRI Phase 8
Desktop control: mouse, keyboard, clipboard, windows, screenshots.
Uses xdotool, wmctrl, xclip, scrot — all confirmed available.
"""
import subprocess, os, re, tempfile

def _run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, "Command timed out."
    except FileNotFoundError:
        return -1, f"{cmd[0]} not found."
    except Exception as e:
        return -1, str(e)

# ── Screenshot ──
def take_screenshot(path: str = None) -> str:
    if not path:
        path = os.path.expanduser(f"~/shrri_screenshot.png")
    code, out = _run(["scrot", path])
    if code == 0:
        return f"✅ Screenshot saved: {path}"
    return f"GAP: screenshot failed — {out.strip()}"

# ── Mouse ──
def mouse_move(x: int, y: int) -> str:
    code, out = _run(["xdotool", "mousemove", str(x), str(y)])
    return f"✅ Mouse moved to ({x}, {y})" if code == 0 else f"GAP: {out.strip()}"

def mouse_click(x: int = None, y: int = None, button: str = "1") -> str:
    if x is not None and y is not None:
        _run(["xdotool", "mousemove", str(x), str(y)])
    code, out = _run(["xdotool", "click", button])
    return f"✅ Clicked at ({x}, {y})" if code == 0 else f"GAP: {out.strip()}"

def mouse_position() -> str:
    code, out = _run(["xdotool", "getmouselocation"])
    return out.strip() if code == 0 else f"GAP: {out.strip()}"

# ── Keyboard ──
def keyboard_type(text: str) -> str:
    code, out = _run(["xdotool", "type", "--clearmodifiers", text])
    return f"✅ Typed: {text[:50]}" if code == 0 else f"GAP: {out.strip()}"

def keyboard_key(key: str) -> str:
    code, out = _run(["xdotool", "key", key])
    return f"✅ Key pressed: {key}" if code == 0 else f"GAP: {out.strip()}"

# ── Clipboard ──
def clipboard_copy(text: str) -> str:
    try:
        p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
        p.communicate(text.encode())
        return f"✅ Copied to clipboard: {text[:50]}"
    except Exception as e:
        return f"GAP: clipboard copy failed — {e}"

def clipboard_paste() -> str:
    code, out = _run(["xclip", "-selection", "clipboard", "-o"])
    return out.strip() if code == 0 else f"GAP: {out.strip()}"

# ── Window Manager ──
def list_windows() -> str:
    code, out = _run(["wmctrl", "-l"])
    if code != 0:
        return f"GAP: {out.strip()}"
    lines = [l for l in out.strip().split("\n") if l]
    if not lines:
        return "No windows found."
    return "Open windows:\n" + "\n".join(f"  {l}" for l in lines)

def focus_window(title: str) -> str:
    code, out = _run(["wmctrl", "-a", title])
    return f"✅ Focused: {title}" if code == 0 else f"GAP: {out.strip()}"

def close_window(title: str) -> str:
    code, out = _run(["wmctrl", "-c", title])
    return f"✅ Closed: {title}" if code == 0 else f"GAP: {out.strip()}"

def get_active_window() -> str:
    code, out = _run(["xdotool", "getactivewindow", "getwindowname"])
    return out.strip() if code == 0 else f"GAP: {out.strip()}"

# ── OCR (route to cloud vision) ──
def ocr_screenshot(path: str = None) -> str:
    if not path:
        path = os.path.expanduser("~/shrri_ocr_screenshot.png")
    take_screenshot(path)
    try:
        import base64
        with open(path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()
        from engine.router import Router
        r = Router()
        result = r.chat(
            "Extract all text visible in this screenshot. Return only the text, no commentary.",
            capability="vision",
            web_search=False
        )
        return result
    except Exception as e:
        return f"GAP: OCR failed — {e}"

# ── Main router ──
def computer_use_query(prompt: str) -> str:
    low = prompt.lower()

    if re.search(r'\bscreenshot\b|\bscreen\s*cap\b', low):
        m = re.search(r'(?:save|to|at)\s+(\S+\.png)', prompt, re.I)
        return take_screenshot(m.group(1) if m else None)

    if re.search(r'\bocr\b|\bread\s+screen\b|\bextract\s+text\b', low):
        return ocr_screenshot()

    if re.search(r'\blist\s+windows\b|\bopen\s+windows\b|\bwindows\b', low):
        return list_windows()

    if re.search(r'\bactive\s+window\b|\bcurrent\s+window\b', low):
        return get_active_window()

    if re.search(r'\bfocus\b|\bswitch\s+to\b', low):
        m = re.search(r'(?:focus|switch\s+to)\s+(.+)', prompt, re.I)
        title = m.group(1).strip() if m else ""
        return focus_window(title) if title else "Specify window title."

    if re.search(r'\bclose\s+window\b', low):
        m = re.search(r'close\s+(?:window\s+)?(.+)', prompt, re.I)
        title = m.group(1).strip() if m else ""
        return close_window(title) if title else "Specify window title."

    if re.search(r'\btype\b|\benter\s+text\b', low):
        m = re.search(r'(?:type|enter\s+text)\s*[:\-]?\s*(.+)', prompt, re.I)
        text = m.group(1).strip() if m else ""
        return keyboard_type(text) if text else "Specify text to type."

    if re.search(r'\bpress\s+key\b|\bkey\b', low):
        m = re.search(r'(?:press\s+key|key)\s*[:\-]?\s*(\S+)', prompt, re.I)
        key = m.group(1).strip() if m else ""
        return keyboard_key(key) if key else "Specify key to press."

    if re.search(r'\bclick\b', low):
        m = re.search(r'click\s+(?:at\s+)?(\d+)[,\s]+(\d+)', prompt, re.I)
        if m:
            return mouse_click(int(m.group(1)), int(m.group(2)))
        return mouse_click()

    if re.search(r'\bmouse\s+(?:move|position|where)\b|\bwhere\s+is\s+(?:the\s+)?mouse\b', low):
        if "move" in low:
            m = re.search(r'move\s+(?:to\s+)?(\d+)[,\s]+(\d+)', prompt, re.I)
            if m:
                return mouse_move(int(m.group(1)), int(m.group(2)))
        return mouse_position()

    if re.search(r'\bcopy\s+to\s+clipboard\b|\bclipboard\s+copy\b', low):
        m = re.search(r'copy\s+to\s+clipboard\s*[:\-]?\s*(.+)', prompt, re.I)
        text = m.group(1).strip() if m else ""
        return clipboard_copy(text) if text else "Specify text to copy."

    if re.search(r'\bpaste\b|\bclipboard\s+content\b|\bwhat.s\s+in\s+clipboard\b', low):
        return clipboard_paste()

    return (
        "Computer Use commands:\n"
        "  screenshot, ocr, list windows, active window,\n"
        "  focus <title>, close window <title>,\n"
        "  type: <text>, press key: <key>,\n"
        "  click at <x> <y>, mouse move <x> <y>,\n"
        "  copy to clipboard: <text>, paste"
    )
