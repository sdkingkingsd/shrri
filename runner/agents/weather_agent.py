"""
Weather Agent — SHRRI Phase 7
Thin wrapper around tools/weather_tool.py.
"""
import logging
logger = logging.getLogger(__name__)

class WeatherAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def run(self, payload: dict) -> str:
        prompt = payload.get("prompt", "")
        if self.verbose:
            logger.info(f"[weather_agent] prompt: {prompt!r}")
        import re
        from tools.weather_tool import get_weather
        # Extract location from prompt
        m = re.search(r"(?:in|for|at)\s+([A-Za-z\s,]+?)(?:\?|$|\.)", prompt, re.IGNORECASE)
        if m:
            location = m.group(1).strip()
        else:
            # Use whole prompt as location fallback
            location = re.sub(r"(?i)(weather|temperature|forecast|what.s the|get|check|how.s the|tell me)", "", prompt).strip(" ?.,")
        if not location:
            return "Please specify a location, e.g. /goal weather: in Chennai"
        if self.verbose:
            logger.info(f"[weather_agent] looking up: {location!r}")
        return get_weather(location)
