"""WhatsApp reader — reads recent messages via Selenium."""
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

        # Wait for chat list
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[@aria-label='Chat list']")))
        time.sleep(4)

        if contact:
            # Use search box (aria-label = "Search or start a new chat")
            search = driver.find_element(By.XPATH, "//*[@aria-label='Search or start a new chat']")
            search.click()
            search.send_keys(contact)
            time.sleep(2)
            # Click first result in chat list
            first = driver.find_elements(By.XPATH, "//*[@aria-label='Chat list']//div[@role='listitem' or @tabindex='-1']")
            if first:
                first[0].click()
            else:
                driver.quit()
                return "GAP: contact not found: " + contact
        else:
            # Click first chat in list
            chats = driver.find_elements(By.XPATH, "//*[@aria-label='Chat list']//*[@tabindex='-1']")
            if not chats:
                driver.quit()
                return "GAP: could not open any chat."
            chats[0].click()

        time.sleep(5)

        # Extract messages
        msgs = driver.find_elements(By.CSS_SELECTOR, "span.selectable-text.copyable-text")
        if not msgs:
            msgs = driver.find_elements(By.XPATH, "//span[@class='selectable-text copyable-text']")

        if not msgs:
            driver.quit()
            return "GAP: chat opened but no messages extracted."

        header = "Recent WhatsApp messages" + (" from " + contact if contact else "") + ":"
        lines = [header]
        seen = set()
        for m in msgs[-15:]:
            t = m.text.strip()
            if t and t not in seen and len(t) > 1:
                seen.add(t)
                lines.append("  • " + t)

        driver.quit()
        return "\n".join(lines) if len(lines) > 1 else "No message text found."

    except Exception as e:
        return "GAP: WhatsApp read failed — " + str(e)
