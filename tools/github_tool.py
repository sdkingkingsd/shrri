"""GitHub tool — git + gh CLI wrapper for the SHRRI repo."""
import re, subprocess

REPO_DIR = "/home/shrridharshan/shrri"

def _run(cmd: list, timeout: int = 20) -> tuple:
    try:
        result = subprocess.run(
            cmd, cwd=REPO_DIR, capture_output=True, text=True, timeout=timeout)
        return result.returncode, (result.stdout or "") + (result.stderr or "")
    except FileNotFoundError:
        return -1, f"{cmd[0]} is not installed."
    except subprocess.TimeoutExpired:
        return -1, f"{cmd[0]} timed out."

def git_status() -> str:
    _, out = _run(["git", "status", "--short", "--branch"])
    return out.strip() or "No changes — working tree clean."

def git_diff() -> str:
    _, out = _run(["git", "diff"])
    return out.strip()[:3000] or "No differences."

def git_commit(message: str = "Update via SHRRI") -> str:
    _run(["git", "add", "-A"])
    code, out = _run(["git", "commit", "-m", message])
    return out.strip() if out.strip() else ("Committed." if code == 0 else "Nothing to commit.")

def git_push() -> str:
    code, out = _run(["git", "push"])
    return out.strip() or ("Pushed." if code == 0 else "Push failed.")

def gh_issues() -> str:
    _, out = _run(["gh", "issue", "list"])
    return out.strip() or "No open issues."

def gh_create_issue(title: str) -> str:
    code, out = _run(["gh", "issue", "create", "--title", title, "--body", "Created via SHRRI."])
    return out.strip() or ("Issue created." if code == 0 else "Failed.")

def gh_prs() -> str:
    _, out = _run(["gh", "pr", "list"])
    return out.strip() or "No open pull requests."

def gh_create_pr() -> str:
    code, out = _run(["gh", "pr", "create", "--fill"])
    return out.strip() or ("PR created." if code == 0 else "Failed.")

def gh_repo_info() -> str:
    _, out = _run(["gh", "repo", "view"])
    return out.strip() or "Could not fetch repo info."

def github_query(prompt: str) -> str:
    low = prompt.lower()
    if re.search(r"\b(status|changes|uncommitted)\b", low):
        return git_status()
    if "diff" in low:
        return git_diff()
    if "commit" in low and "pr" not in low and "pull request" not in low:
        m = re.search(r"commit\s*(?:message)?\s*[:\-]?\s*(.+)$", prompt, re.I)
        msg = m.group(1).strip() if m else "Update via SHRRI"
        return git_commit(msg)
    if "push" in low:
        return git_push()
    if re.search(r"\bcreate\b.*\bissue\b|\bopen\b.*\bissue\b", low):
        m = re.search(r"issue\s*[:\-]?\s*(.+)$", prompt, re.I)
        title = m.group(1).strip() if m else "New issue from SHRRI"
        return gh_create_issue(title)
    if "issue" in low:
        return gh_issues()
    if re.search(r"\bcreate\b.*\bpr\b|\bopen\b.*\bpr\b", low):
        return gh_create_pr()
    if re.search(r"\b(pr|pull request)s?\b", low):
        return gh_prs()
    if re.search(r"\brepo\b.*\binfo\b|\babout\b.*\brepo\b", low):
        return gh_repo_info()
    return "GitHub tool: status, diff, commit, push, issues, create issue, prs, create pr, repo info"
