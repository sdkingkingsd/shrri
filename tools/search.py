from ddgs import DDGS
import time

MAX_RESULTS = 2
MAX_BODY_LENGTH = 300
MAX_SEARCHES = 3


def search(query: str, max_results: int = MAX_RESULTS) -> str:
    """
    Search the web using DuckDuckGo.
    Returns clean text summary for SHRRI to use.
    Privacy: No API key, no tracking, no data stored.
    """
    try:
        results = DDGS().text(query, max_results=max_results)

        if not results:
            return f"No results found for: {query}"

        output = f"Web search results for: '{query}'\n"
        output += "=" * 50 + "\n"

        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            body = r.get("body", "")[:MAX_BODY_LENGTH]
            url = r.get("href", "")
            output += f"\n[{i}] {title}\n"
            output += f"    {body}...\n"
            output += f"    Source: {url}\n"

        return output

    except Exception as e:
        return f"Search failed: {str(e)}"


def should_search(message: str) -> bool:
    """
    Decide if a message needs web search.
    Returns True if the question needs live/current data.
    """
    triggers = [
        "latest", "recent", "today", "now", "current",
        "2026", "news", "weather", "price", "update",
        "what is happening", "who won", "when is",
        "how much is", "live", "breaking", "trending",
        "new release", "just announced", "right now",
        "search", "find", "look up", "google",
    ]
    message_lower = message.lower()
    return any(trigger in message_lower for trigger in triggers)


def smart_search(message: str) -> str:
    """
    Intelligently decides whether to search and returns results.
    Called by SHRRI engine before sending to LLM.
    """
    if not should_search(message):
        return ""

    # Clean up the query — remove filler words
    query = message.strip()
    query = query.replace("what is", "").replace("tell me about", "")
    query = query.replace("can you find", "").replace("search for", "")
    query = query.replace("look up", "").replace("google", "")
    query = query.strip()

    result = search(query, max_results=MAX_RESULTS)
    return result


if __name__ == "__main__":
    # Quick test
    print(search("latest AI news 2026", max_results=2))
