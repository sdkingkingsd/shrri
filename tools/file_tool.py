"""File manager tool — find and open files."""
import subprocess, re, os

def file_search(message: str) -> str:
    msg = message.lower()
    try:
        if "downloads" in msg:
            directory = os.path.expanduser("~/Downloads")
        elif "desktop" in msg:
            directory = os.path.expanduser("~/Desktop")
        elif "documents" in msg:
            directory = os.path.expanduser("~/Documents")
        elif "pictures" in msg or "photos" in msg:
            directory = os.path.expanduser("~/Pictures")
        elif "music" in msg:
            directory = os.path.expanduser("~/Music")
        elif "videos" in msg:
            directory = os.path.expanduser("~/Videos")
        else:
            directory = os.path.expanduser("~")

        ext_map = {
            "pdf": "*.pdf", "pdfs": "*.pdf",
            "image": "*.png", "images": "*.png",
            "video": "*.mp4", "videos": "*.mp4",
            "python": "*.py", "zip": "*.zip",
            "excel": "*.xlsx", "text": "*.txt",
        }

        pattern = None
        for key, val in ext_map.items():
            if key in msg:
                pattern = val
                break

        if pattern:
            result = subprocess.run(
                ["find", directory, "-iname", pattern, "-type", "f"],
                capture_output=True, text=True, timeout=10
            )
        else:
            result = subprocess.run(
                ["find", directory, "-maxdepth", "2", "-type", "f"],
                capture_output=True, text=True, timeout=10
            )

        files = [f for f in result.stdout.strip().split("\n") if f]
        if not files:
            return f"No files found in {directory}."

        lines = [f"Found {len(files)} file(s) in {directory}:"]
        for f in files[:15]:
            size = os.path.getsize(f)
            size_str = f"{size//1024}KB" if size > 1024 else f"{size}B"
            lines.append(f"  {os.path.basename(f)} ({size_str})")
        if len(files) > 15:
            lines.append(f"  ... and {len(files)-15} more")
        return "\n".join(lines)
    except Exception as e:
        return f"GAP: file search failed — {e}"

def open_file(message: str) -> str:
    try:
        m = re.search(r"open\s+(.+)$", message, re.IGNORECASE)
        if not m:
            return "GAP: specify file to open."
        filename = m.group(1).strip()
        result = subprocess.run(
            ["find", os.path.expanduser("~"), "-iname", f"*{filename}*", "-type", "f"],
            capture_output=True, text=True, timeout=10
        )
        files = [f for f in result.stdout.strip().split("\n") if f]
        if not files:
            return f"GAP: file not found: {filename}"
        subprocess.Popen(["xdg-open", files[0]])
        return f"Opening: {files[0]}"
    except Exception as e:
        return f"GAP: could not open file — {e}"
