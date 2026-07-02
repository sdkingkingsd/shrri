"""
browser_agent.py — Lightweight autonomous browser using Playwright + SHRRI LLM
No browser-use dependency needed
"""
from tools.browser import browser_action

def browse_agent(task: str) -> str:
    """
    Simple autonomous browse: open URL from task, extract content, 
    let SHRRI's LLM summarize/answer based on task.
    """
    import re
    from engine.router import Router

    url_match = re.search(r"https?://\S+", task)
    if url_match:
        url = url_match.group()
    else:
        # Fall back to a bare domain like "example.com" or "www.example.com"
        bare_match = re.search(r"\b((?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,})\b", task)
        if not bare_match:
            return "❌ No URL found in task."
        url = "https://" + bare_match.group()
    content = browser_action("open", url=url)

    if content.startswith("Browser error"):
        return content

    r = Router()
    answer = r.chat(
        f"You have already browsed the page. Answer the task directly using the content below. Do not say you cannot access websites.\n\nTask: {task}\n\nPage content:\n{content[:3000]}",
        task="fast",
        web_search=False
    )
    return answer
