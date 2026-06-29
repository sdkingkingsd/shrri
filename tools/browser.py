from playwright.sync_api import sync_playwright
import concurrent.futures
import re

_TIMEOUT = 15000

def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:3000]

def browser_action(action: str, **params) -> str:
    url = params.get("url", "")
    if not url:
        return "No URL provided."
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=_TIMEOUT, wait_until="domcontentloaded")

            if action == "open":
                text = page.inner_text("body")
                browser.close()
                return _clean(text)

            elif action == "get_text":
                selector = params.get("selector", "body")
                text = page.locator(selector).first.inner_text(timeout=_TIMEOUT)
                browser.close()
                return _clean(text)

            elif action == "click":
                selector = params.get("selector", "")
                if not selector:
                    browser.close()
                    return "No selector provided."
                page.locator(selector).first.click(timeout=_TIMEOUT)
                page.wait_for_load_state("domcontentloaded")
                text = page.inner_text("body")
                browser.close()
                return _clean(text)

            elif action == "type_text":
                selector = params.get("selector", "")
                text = params.get("text", "")
                submit = params.get("submit", False)
                if not selector:
                    browser.close()
                    return "No selector provided."
                page.locator(selector).first.fill(text, timeout=_TIMEOUT)
                if submit:
                    page.keyboard.press("Enter")
                    page.wait_for_load_state("domcontentloaded")
                result = page.inner_text("body")
                browser.close()
                return _clean(result)

            elif action == "screenshot":
                path = params.get("path", "/tmp/shrri_ss.png")
                page.screenshot(path=path, full_page=False)
                browser.close()
                return f"Screenshot saved to {path}"

            else:
                browser.close()
                return f"Unknown action: {action}"

    except Exception as e:
        return f"Browser error: {e}"
