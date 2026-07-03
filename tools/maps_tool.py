"""Maps tool — search places, get directions, coordinates via Nominatim (no API key needed)."""
import urllib.request, urllib.parse, json, re

def maps_search(query: str) -> str:
    """Search for a place and return its coordinates + address."""
    try:
        q = urllib.parse.quote(query)
        url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=3&addressdetails=1"
        req = urllib.request.Request(url, headers={"User-Agent": "SHRRI/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            results = json.loads(r.read().decode())
        if not results:
            return f"No results found for: {query}"
        lines = [f"📍 Results for '{query}':"]
        for i, r in enumerate(results, 1):
            name = r.get("display_name", "Unknown")
            lat, lon = r.get("lat"), r.get("lon")
            lines.append(f"{i}. {name}")
            lines.append(f"   📌 {lat}, {lon}")
            lines.append(f"   🔗 https://www.openstreetmap.org/?mlat={lat}&mlon={lon}")
        return "\n".join(lines)
    except Exception as e:
        return f"GAP: maps search failed — {e}"

def maps_directions(origin: str, destination: str) -> str:
    """Get a directions link between two places."""
    try:
        o = urllib.parse.quote(origin)
        d = urllib.parse.quote(destination)
        url = f"https://www.openstreetmap.org/directions?from={o}&to={d}"
        return (
            f"🗺 Directions: {origin} → {destination}\n"
            f"🔗 {url}\n"
            f"(Open link for turn-by-turn directions)"
        )
    except Exception as e:
        return f"GAP: directions failed — {e}"

def maps_query(prompt: str) -> str:
    """Route maps queries — directions or place search."""
    m = re.search(r'(?:from|directions?\s+from)\s+(.+?)\s+to\s+(.+)', prompt, re.I)
    if m:
        return maps_directions(m.group(1).strip(), m.group(2).strip())
    # Strip filler words for search
    query = re.sub(r'(?i)^(find|search|locate|where is|map of|show me)\s+', '', prompt).strip()
    return maps_search(query)
