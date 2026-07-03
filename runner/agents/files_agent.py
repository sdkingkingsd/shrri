"""
Files Agent — SHRRI Phase 7
Thin wrapper around tools/file_tool.py for file search and open.
"""
import logging
logger = logging.getLogger(__name__)

class FilesAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "")
        if self.verbose:
            logger.info(f"[files_agent] prompt: {prompt!r}")
        from tools.file_tool import file_search, open_file
        if "open" in prompt.lower():
            return open_file(prompt)
        return file_search(prompt)
