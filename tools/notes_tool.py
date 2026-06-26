"""Notes tool — save and retrieve personal notes."""
import json
import os
from datetime import datetime
import pytz

NOTES_FILE = os.path.expanduser("~/.shrri/notes.json")
IST = pytz.timezone("Asia/Kolkata")

def _load():
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE) as f:
            return json.load(f)
    return []

def _save(notes):
    with open(NOTES_FILE, "w") as f:
        json.dump(notes, f, indent=2)

def save_note(message: str) -> str:
    try:
        # Extract note text
        text = message
        for marker in ["save note:", "save note ", "note:", "note ", "remember "]:
            idx = message.lower().find(marker)
            if idx != -1:
                text = message[idx + len(marker):].strip()
                break
        if not text:
            return "GAP: no note text found."
        notes = _load()
        note = {
            "id": len(notes) + 1,
            "text": text,
            "time": datetime.now(IST).strftime("%Y-%m-%d %I:%M %p")
        }
        notes.append(note)
        _save(notes)
        return f"📝 Note saved: \"{text}\""
    except Exception as e:
        return f"GAP: could not save note — {e}"

def show_notes(message: str = "") -> str:
    try:
        notes = _load()
        if not notes:
            return "📝 No notes saved yet."
        # Search filter
        query = ""
        for marker in ["search notes ", "find note ", "notes about "]:
            idx = message.lower().find(marker)
            if idx != -1:
                query = message[idx + len(marker):].strip().lower()
                break
        if query:
            notes = [n for n in notes if query in n["text"].lower()]
            if not notes:
                return f"📝 No notes found matching '{query}'."
        lines = [f"📝 Your notes ({len(notes)}):"]
        for n in notes[-10:]:  # show last 10
            lines.append(f"  [{n['id']}] {n['time']} — {n['text']}")
        return "\n".join(lines)
    except Exception as e:
        return f"GAP: could not read notes — {e}"

def delete_note(message: str) -> str:
    try:
        import re
        m = re.search(r"\d+", message)
        if not m:
            return "GAP: specify note number. Try: delete note 3"
        note_id = int(m.group())
        notes = _load()
        notes = [n for n in notes if n["id"] != note_id]
        _save(notes)
        return f"📝 Note {note_id} deleted."
    except Exception as e:
        return f"GAP: could not delete note — {e}"
