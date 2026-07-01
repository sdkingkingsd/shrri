"""
self_edit.py - Lets SHRRI edit its own files (~/shrri, ~/.shrri only),
with an automatic backup before every change.

SECURITY NOTE: This module must ONLY ever be called from telegram_bot.py,
which already restricts access to your own Telegram user ID. Never call
this from the general dispatcher, since that path is also reachable by
WhatsApp messages from other people.
"""
import os
import shutil
import datetime

ALLOWED_ROOTS = [
    os.path.expanduser("~/shrri"),
    os.path.expanduser("~/.shrri"),
]
BACKUP_DIR = os.path.expanduser("~/.shrri/file_backups")

def _is_allowed(path: str) -> bool:
    real = os.path.realpath(path)
    return any(real.startswith(os.path.realpath(root)) for root in ALLOWED_ROOTS)

def _backup(path: str) -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = os.path.basename(path) + "." + ts + ".bak"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    if os.path.exists(path):
        shutil.copy2(path, backup_path)
    return backup_path

def read_file(path: str) -> str:
    path = os.path.expanduser(path)
    if not _is_allowed(path):
        return "BLOCKED: only files inside ~/shrri or ~/.shrri can be accessed."
    if not os.path.exists(path):
        return "GAP: file not found - " + path
    try:
        with open(path, "r") as f:
            content = f.read()
        return content[:5000]
    except Exception as e:
        return "GAP: could not read file - " + str(e)

def write_file(path: str, content: str) -> str:
    path = os.path.expanduser(path)
    if not _is_allowed(path):
        return "BLOCKED: only files inside ~/shrri or ~/.shrri can be edited."
    try:
        backup_path = _backup(path)
        with open(path, "w") as f:
            f.write(content)
        return "Saved. Backup created at: " + backup_path
    except Exception as e:
        return "GAP: write failed - " + str(e)

def list_backups(filename: str = None) -> str:
    if not os.path.exists(BACKUP_DIR):
        return "No backups yet."
    files = sorted(os.listdir(BACKUP_DIR))
    if filename:
        files = [f for f in files if filename in f]
    if not files:
        return "No backups found."
    return "\n".join(files[-20:])

def restore_backup(backup_filename: str, target_path: str) -> str:
    target_path = os.path.expanduser(target_path)
    if not _is_allowed(target_path):
        return "BLOCKED: target must be inside ~/shrri or ~/.shrri."
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    if not os.path.exists(backup_path):
        return "GAP: backup not found - " + backup_filename
    shutil.copy2(backup_path, target_path)
    return "Restored " + target_path + " from " + backup_filename

# ---- Natural language edit flow (preview + confirm) ----
_pending_edit = {}  # single-user system, module-level state is fine

def _list_editable_files() -> list:
    files = []
    for root in ALLOWED_ROOTS:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in
                           (".git", "node_modules", "__pycache__", "file_backups")]
            for fn in filenames:
                if fn.endswith((".bak",)):
                    continue
                files.append(os.path.join(dirpath, fn))
    return files

def _find_explicit_path(instruction: str):
    """If the instruction contains an explicit path mentioning ~/shrri or
    ~/.shrri (or a bare filename that uniquely matches a real file), return
    its resolved absolute path. Otherwise return None."""
    import re
    candidates = _list_editable_files()

    # Look for explicit ~/shrri/... or ~/.shrri/... style paths
    m = re.search(r"~?/(?:home/[^/\s]+/)?(?:\.?shrri/[^\s]+)", instruction)
    if m:
        expanded = os.path.realpath(os.path.expanduser(m.group(0)))
        for c in candidates:
            if os.path.realpath(c) == expanded:
                return c

    # Fall back: look for a bare filename mentioned in the instruction that
    # uniquely matches exactly one real file (e.g. "test_file.txt")
    words = re.findall(r"[\w\-.]+\.\w+", instruction)
    matches = []
    for w in words:
        hits = [c for c in candidates if os.path.basename(c) == w]
        matches.extend(hits)
    matches = list(set(matches))
    if len(matches) == 1:
        return matches[0]

    return None

def propose_edit(instruction: str, router) -> str:
    """
    Figure out which file the instruction refers to, generate new content,
    and store it as a pending edit awaiting confirmation. Returns a preview
    string to show the user.
    """
    explicit = _find_explicit_path(instruction)
    if explicit:
        picked = explicit
    else:
        candidates = _list_editable_files()
        candidate_list = "\n".join(candidates[:200])

        pick_prompt = (
        "Here is a list of files SHRRI is allowed to edit:\n"
        + candidate_list +
        "\n\nThe user said: \"" + instruction + "\"\n\n"
        "Reply with ONLY the single full file path from the list above that "
        "this instruction is most likely about. If no file clearly matches, "
        "reply exactly: NONE"
    )
        picked = router.chat(pick_prompt, task="fast", web_search=False).strip()

    if picked == "NONE" or not os.path.exists(picked) or not _is_allowed(picked):
        return ("Couldn't confidently tell which file you mean. "
                "Please specify the exact filename or use /editfile.")

    path = picked
    if not _is_allowed(path):
        return "BLOCKED: that file is outside the allowed folders."

    try:
        with open(path, "r") as f:
            old_content = f.read()
    except Exception as e:
        return "GAP: could not read " + path + " - " + str(e)

    gen_prompt = (
        "Current content of " + path + ":\n---\n" + old_content[:3000] + "\n---\n\n"
        "The user wants this change: \"" + instruction + "\"\n\n"
        "Output ONLY the complete new file content after applying this change. "
        "No explanation, no markdown fences, just the raw new file content."
    )
    new_content = router.chat(gen_prompt, task="fast", web_search=False)

    _pending_edit["path"] = path
    _pending_edit["new_content"] = new_content
    _pending_edit["old_content"] = old_content

    preview = (
        "Proposed edit to: " + path + "\n\n"
        "--- OLD (first 300 chars) ---\n" + old_content[:300] + "\n\n"
        "--- NEW (first 300 chars) ---\n" + new_content[:300] + "\n\n"
        "Reply 'yes' to save, or anything else to cancel."
    )
    return preview

def confirm_pending_edit() -> str:
    if not _pending_edit:
        return "No pending edit to confirm."
    path = _pending_edit["path"]
    new_content = _pending_edit["new_content"]
    result = write_file(path, new_content)
    _pending_edit.clear()
    return result

def cancel_pending_edit() -> str:
    _pending_edit.clear()
    return "Cancelled. No changes made."

def has_pending_edit() -> bool:
    return bool(_pending_edit)
