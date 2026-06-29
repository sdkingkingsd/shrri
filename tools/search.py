"""
SHRRI Web Search — multi-backend, key-free.

Priority:
  1. DuckDuckGo (ddgs)
  2. SearXNG public instance (fallback)

Plus web_extract: fetch and read a full page as clean text.
"""
import re, time
import requests
from bs4 import BeautifulSoup

MAX_RESULTS    = 5
MAX_BODY       = 500
MAX_EXTRACT    = 3000
SEARXNG_HOSTS  = [
    "https://searx.be",
    "https://search.bus-hit.me",
    "https://searxng.site",
]

# ── Backend 1: DuckDuckGo ─────────────────────────────────────────────────
def _ddg(query: str, max_results: int) -> list:
    try:
        from ddgs import DDGS
        results = DDGS().text(query, max_results=max_results)
        return [
            {"title": r.get("title",""), "body": r.get("body",""), "url": r.get("href","")}
            for r in (results or [])
        ]
    except Exception as e:
        print(f"[search] DDG failed: {e}")
        return []

# ── Backend 2: SearXNG public instances ───────────────────────────────────
def _searxng(query: str, max_results: int) -> list:
    for host in SEARXNG_HOSTS:
        try:
            r = requests.get(
                f"{host}/search",
                params={"q": query, "format": "json", "engines": "google,bing,duckduckgo"},
                timeout=6,
                headers={"User-Agent": "SHRRI/1.0"}
            )
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])[:max_results]
                return [
                    {"title": x.get("title",""), "body": x.get("content",""), "url": x.get("url","")}
                    for x in results
                ]
        except Exception as e:
            print(f"[search] SearXNG {host} failed: {e}")
            continue
    return []

# ── web_extract: fetch full page, return clean text ───────────────────────
def web_extract(url: str, max_length: int = MAX_EXTRACT) -> str:
    """Fetch a URL and return clean readable text (no HTML)."""
    try:
        r = requests.get(url, timeout=8, headers={
            "User-Agent": "Mozilla/5.0 (compatible; SHRRI/1.0)"
        })
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # Remove noise
        for tag in soup(["script","style","nav","footer","header","aside","form"]):
            tag.decompose()
        # Get main content
        main = soup.find("main") or soup.find("article") or soup.find("body")
        if not main:
            return "Could not extract content from page."
        text = re.sub(r"\n{3,}", "\n\n", main.get_text(separator="\n")).strip()
        return text[:max_length] + ("..." if len(text) > max_length else "")
    except Exception as e:
        return f"Extract failed: {e}"

# ── Core search with fallback ─────────────────────────────────────────────
def search(query: str, max_results: int = MAX_RESULTS) -> str:
    """Search with DDG, fall back to SearXNG. Returns formatted text."""
    results = _ddg(query, max_results)
    if not results:
        print("[search] DDG returned nothing, trying SearXNG...")
        results = _searxng(query, max_results)
    if not results:
        return f"No results found for: {query}"

    out = f"Web search: '{query}'\n" + "="*50 + "\n"
    for i, r in enumerate(results, 1):
        body = r["body"][:MAX_BODY]
        out += f"\n[{i}] {r['title']}\n    {body}...\n    Source: {r['url']}\n"
    return out

# ── Smart trigger detection ───────────────────────────────────────────────
def should_search(message: str) -> bool:
    triggers = [
        "latest", "recent", "today", "now", "current",
        "2025", "2026", "news", "weather", "price", "update",
        "what is happening", "who won", "when is",
        "how much is", "live", "breaking", "trending",
        "new release", "just announced", "right now",
        "search", "find", "look up", "google",
        "what happened", "score", "result", "match",
        "stock", "crypto", "rate", "exchange",
    ]
    msg = message.lower()
    return any(t in msg for t in triggers)

def smart_search(message: str) -> str:
    """Called by router — decides whether to search and returns context."""
    if not should_search(message):
        return ""
    query = message.strip()
    for filler in ["what is","tell me about","can you find","search for",
                   "look up","google","find me","what are"]:
        query = query.replace(filler, "")
    query = query.strip()
    return search(query, max_results=MAX_RESULTS)

# ── Test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(search("latest AI news 2026", max_results=3))
    print("\n--- Extract test ---")
    print(web_extract("https://en.wikipedia.org/wiki/Artificial_intelligence", max_length=500))
