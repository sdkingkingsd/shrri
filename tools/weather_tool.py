"""Weather tool — fetches live weather from wttr.in (no API key needed)."""
import urllib.request
import json

def get_weather(location: str) -> str:
    """Get current weather for a location."""
    try:
        location = location.strip().replace(" ", "+")
        url = f"https://wttr.in/{location}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "SHRRI/1.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())

        current = data["current_condition"][0]
        area = data["nearest_area"][0]

        city = area["areaName"][0]["value"]
        country = area["country"][0]["value"]
        temp_c = current["temp_C"]
        feels_c = current["FeelsLikeC"]
        humidity = current["humidity"]
        desc = current["weatherDesc"][0]["value"]
        wind_kmph = current["windspeedKmph"]

        return (
            f"🌤 Weather in {city}, {country}:\n"
            f"  {desc}, {temp_c}°C (feels like {feels_c}°C)\n"
            f"  💧 Humidity: {humidity}%  💨 Wind: {wind_kmph} km/h"
        )
    except Exception as e:
        return f"GAP: could not fetch weather for '{location}' — {e}"
