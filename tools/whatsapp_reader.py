"""WhatsApp reader — reads recent messages with sender names."""
import time, re

CHROMEDRIVER = "/home/shrridharshan/.wdm/drivers/chromedriver/linux64/149.0.7827.155/chromedriver-linux64/chromedriver"
CHROME_PROFILE = "/home/shrridharshan/.shrri/chrome_profile"

def read_whatsapp(message="", contact=""):
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        if not contact:
            m = re.search(r"(?:from|with|messages from)\s+(.+?)(?:\s+on whatsapp|$)", message, re.IGNORECASE)
            if m:
                contact = m.group(1).strip()

        options = Options()
        options.add_argument("--user-data-dir=" + CHROME_PROFILE)
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(service=Service(CHROMEDRIVER), options=options)
        wait = WebDriverWait(driver, 30)
        driver.get("https://web.whatsapp.com")
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[@aria-label='Chat list']")))
        time.sleep(4)

        if contact:
            search = driver.find_element(By.XPATH, "//*[@aria-label='Search or start a new chat']")
            search.click()
            search.send_keys(contact)
            time.sleep(2)
            chats = driver.find_elements(By.XPATH, "//*[@aria-label='Chat list']//*[@tabindex='-1']")
            if not chats:
                driver.quit()
                return "GAP: contact not found: " + contact
            chats[0].click()
        else:
            chats = driver.find_elements(By.XPATH, "//*[@aria-label='Chat list']//*[@tabindex='-1']")
            if not chats:
                driver.quit()
                return "GAP: could not open any chat."
            # Prefer the first 1-on-1 chat over a group chat — group chats can have
            # different DOM structure (member lists, etc.) that confuses the message
            # selectors and previously leaked phone numbers. We detect a group by
            # checking if the chat row contains a "group" icon/aria-label.
            chosen = chats[0]
            for c in chats[:10]:  # only check the first 10 for speed
                try:
                    is_group = c.find_elements(By.XPATH, ".//*[contains(@aria-label,'Group') or contains(@title,'Group')]")
                    if not is_group:
                        chosen = c
                        break
                except Exception:
                    continue
            chosen.click()

        time.sleep(5)

        # Get message rows — each row has optional sender + text
        rows = driver.find_elements(By.XPATH, "//div[contains(@class,'message-in') or contains(@class,'message-out')]")
        
        if not rows:
            # fallback — SCOPED to the actual message panel only (#main),
            # never the whole page. The unscoped version was picking up
            # text from sidebars/group-info panels (e.g. member lists),
            # which leaked phone numbers in group chats.
            try:
                panel = driver.find_element(By.CSS_SELECTOR, "#main")
                msgs = panel.find_elements(By.CSS_SELECTOR, "span.selectable-text.copyable-text")
            except Exception:
                msgs = []
            if not msgs:
                driver.quit()
                return "GAP: no messages found (chat may still be loading or unsupported group format)."
            lines = ["Recent messages:"]
            seen = set()
            for m in msgs[-15:]:
                t = m.text.strip()
                if t and t not in seen:
                    seen.add(t)
                    lines.append("  • " + t)
            driver.quit()
            return "\n".join(lines)

        lines = ["Recent WhatsApp messages" + (" from " + contact if contact else "") + ":"]
        seen = set()
        for row in rows[-15:]:
            try:
                # Try to get sender name (only in group chats)
                try:
                    sender = row.find_element(By.XPATH, ".//span[@aria-label]").get_attribute("aria-label")
                    if sender and len(sender) < 40:
                        sender = sender.replace(":", "").strip()
                    else:
                        sender = None
                except Exception:
                    sender = None

                # Determine direction
                cls = row.get_attribute("class") or ""
                direction = "You" if "message-out" in cls else (sender or "Them")

                # Get message text
                try:
                    txt = row.find_element(By.CSS_SELECTOR, "span.selectable-text.copyable-text").text.strip()
                except Exception:
                    txt = row.text.strip().split("\n")[0]

                if txt and txt not in seen and len(txt) > 1:
                    seen.add(txt)
                    lines.append("  [" + direction + "] " + txt)
            except Exception:
                continue

        driver.quit()
        return "\n".join(lines) if len(lines) > 1 else "No messages found."

    except Exception as e:
        return "GAP: WhatsApp read failed — " + str(e)
