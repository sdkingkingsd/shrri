"""Maps Agent — SHRRI Phase 7"""
import logging
logger = logging.getLogger(__name__)

class MapsAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "")
        if self.verbose:
            logger.info(f"[maps_agent] prompt: {prompt!r}")
        from tools.maps_tool import maps_query
        return maps_query(prompt)
