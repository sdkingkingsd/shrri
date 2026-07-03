"""
GitHub Agent — SHRRI AI OS v2 (Phase 5)

Thin wrapper around the real `gh` CLI (already authenticated as
sdkingkingsd with repo/workflow/gist/read:org scopes) and plain `git`
subprocess calls for the local ~/shrri repo. No new GitHub API client
here — gh already handles auth, pagination, and formatting.

Intent routing (checked in order):
  - "status"/"changes"/"diff" (local repo)   -> git status / git diff
  - "commit"                                  -> git add -A + git commit
  - "push"                                    -> git push
  - "issues" (list)                           -> gh issue list
  - "create issue" / "open issue"             -> gh issue create
  - "pull request"/"pr" (list)                -> gh pr list
  - "create pr"/"open pr"                     -> gh pr create
  - "repo info"/"about this repo"             -> gh repo view
  - everything else                           -> explain available commands
"""

import re
import subprocess
from tools.github_tool import github_query

_REPO_DIR = "/home/shrridharshan/shrri"


def _run(cmd: list, timeout: int = 20) -> tuple:
    try:
        result = subprocess.run(
            cmd, cwd=_REPO_DIR, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, (result.stdout or "") + (result.stderr or "")
    except FileNotFoundError:
        return -1, f"{cmd[0]} is not installed on this machine."
    except subprocess.TimeoutExpired:
        return -1, f"{cmd[0]} command timed out."


class GitHubAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "").strip()
        low = prompt.lower()
        if self.verbose:
            print(f"[github_agent] Handling: {prompt[:80]!r}")

        return github_query(prompt)

        # Local repo status / diff (kept for reference, unreachable)
        if re.search(r"\b(status|changes|what.?s changed|uncommitted)\b", low):
            code, out = _run(["git", "status", "--short", "--branch"])
            return out.strip() or "No changes — working tree clean."

        if "diff" in low:
            code, out = _run(["git", "diff"])
            return (out.strip()[:3000] or "No differences.")

        # Commit (safe: only commits what's already staged/modified locally)
        if "commit" in low and "pull request" not in low and "pr" not in low:
            msg_match = re.search(r"commit\s*(?:message)?\s*[:\-]?\s*(.+)$", prompt, re.IGNORECASE)
            message = msg_match.group(1).strip() if msg_match and msg_match.group(1).strip() else "Update via SHRRI GitHub Agent"
            code1, out1 = _run(["git", "add", "-A"])
            code2, out2 = _run(["git", "commit", "-m", message])
            if code2 != 0:
                return f"Commit failed or nothing to commit:\n{out2.strip()}"
            return out2.strip()

        # Push
        if "push" in low:
            code, out = _run(["git", "push"])
            return out.strip() or ("Pushed." if code == 0 else "Push failed.")

        # Issues
        if re.search(r"\bcreate\b.*\bissue\b|\bopen\b.*\bissue\b", low):
            title_match = re.search(r"issue\s*[:\-]?\s*(.+)$", prompt, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match and title_match.group(1).strip() else "New issue from SHRRI"
            code, out = _run(["gh", "issue", "create", "--title", title, "--body", "Created via SHRRI GitHub Agent."])
            return out.strip() or ("Issue created." if code == 0 else "Issue creation failed.")

        if "issue" in low:
            code, out = _run(["gh", "issue", "list"])
            return out.strip() or "No open issues."

        # Pull requests
        if re.search(r"\bcreate\b.*\b(pr|pull request)\b|\bopen\b.*\b(pr|pull request)\b", low):
            code, out = _run(["gh", "pr", "create", "--fill"])
            return out.strip() or ("PR created." if code == 0 else "PR creation failed.")

        if re.search(r"\b(pr|pull request)s?\b", low):
            code, out = _run(["gh", "pr", "list"])
            return out.strip() or "No open pull requests."

        # Repo info
        if re.search(r"\brepo\b.*\binfo\b|\babout\b.*\brepo\b|\brepository\b", low):
            code, out = _run(["gh", "repo", "view"])
            return out.strip() or "Could not fetch repo info."

        return (
            "I can check local git status/diff, commit and push changes, "
            "list or create GitHub issues, list or create pull requests, "
            "or show repo info — say which one you want."
        )
