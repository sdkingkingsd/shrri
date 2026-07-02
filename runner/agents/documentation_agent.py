"""
Documentation Agent — SHRRI AI OS v2 (Phase 5)

Unlike most Phase 5 agents, there's no existing "doc generation" tool
to wrap — so this agent uses the Router (like Coding Agent) to actually
write documentation content, and tools.self_edit for any real file I/O
(read/write), since that module already has the safety net this needs:
automatic backups before every write, and a hard restriction to files
inside ~/shrri or ~/.shrri only.

Intent routing (checked in order):
  - "read"/"show" + a file path        -> self_edit.read_file
  - "write"/"save"/"update" + a path   -> generate doc content via Router,
                                           then self_edit.write_file
  - everything else                    -> generate documentation content
                                           via Router and return it as text
                                           (no file write unless a path
                                           was given, so nothing is
                                           silently written to disk)
"""

import re

from engine.router import Router
from tools.self_edit import read_file, write_file

_DOC_SYSTEM_PROMPT = (
    "You are a documentation specialist. Write clear, accurate, "
    "well-structured documentation (README sections, docstrings, code "
    "summaries, usage guides) based on the request. Prefer concise, "
    "practical explanations with real examples over vague prose. If "
    "asked to document code you weren't given, say so rather than "
    "inventing behavior you can't verify."
)

_PATH_RE = re.compile(r"(~?/?(?:[\w\-.]+/)*[\w\-.]+\.\w+)")


_REPO_ROOT = "/home/shrridharshan/shrri"


class DocumentationAgent:
    def __init__(self, verbose: bool = False):
        self._router = Router()
        self.verbose = verbose

    def _extract_path(self, prompt: str):
        m = _PATH_RE.search(prompt)
        return m.group(1) if m else None

    def _grep_codebase(self, prompt: str) -> str:
        """
        Best-effort grounding: if the request references a SHRRI-specific
        term (a slash-command like /goal, or a distinctive identifier),
        grep the real source for matching lines so the LLM documents what
        the code actually does instead of guessing from generic training
        knowledge about similarly-named features elsewhere.
        """
        import subprocess

        terms = re.findall(r"/\w+", prompt)  # slash-commands like /goal
        terms += re.findall(r"\b[A-Z][a-zA-Z]{3,}(?:Agent|Engine|Manager)\b", prompt)
        if not terms:
            return ""

        snippets = []
        for term in terms[:3]:
            try:
                result = subprocess.run(
                    ["grep", "-rn", "--include=*.py", term, _REPO_ROOT],
                    capture_output=True, text=True, timeout=10,
                )
                lines = [l for l in result.stdout.splitlines() if "__pycache__" not in l][:15]
                if lines:
                    snippets.append(f"Matches for '{term}':\n" + "\n".join(lines))
            except Exception:
                continue

        return "\n\n".join(snippets)

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "").strip()
        low = prompt.lower()
        if self.verbose:
            print(f"[documentation_agent] Handling: {prompt[:80]!r}")

        path = self._extract_path(prompt)

        # READ an existing doc/file
        if path and re.search(r"\b(read|show|display|what's in)\b", low):
            return read_file(path)

        # WRITE/SAVE/UPDATE a doc to a real path
        if path and re.search(r"\b(write|save|update|create)\b", low):
            response = self._router.chat(
                prompt,
                system=_DOC_SYSTEM_PROMPT,
                web_search=False,
                capability="reasoning",
            )
            if not response or not response.strip():
                raise RuntimeError("Documentation agent got an empty response from all providers")
            result = write_file(path, response)
            if result.startswith("BLOCKED") or result.startswith("GAP:"):
                return result
            return f"{result}\n\n---\n{response}"

        # Default: generate documentation content, return as text only.
        # Ground it in real source if the request references a SHRRI-
        # specific command/class, instead of letting the LLM guess.
        grounding = self._grep_codebase(prompt)
        full_prompt = prompt
        if grounding:
            full_prompt = (
                f"{prompt}\n\n"
                f"Here is the REAL source code relevant to this request — "
                f"base your answer on this, not on prior assumptions:\n{grounding}"
            )

        response = self._router.chat(
            full_prompt,
            system=_DOC_SYSTEM_PROMPT,
            web_search=False,
            capability="reasoning",
        )
        if not response or not response.strip():
            raise RuntimeError("Documentation agent got an empty response from all providers")
        return response
