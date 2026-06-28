"""WhatsApp tool — sends via Selenium."""
import re, time, urllib.parse

CHROMEDRIVER = "/home/shrridharshan/.wdm/drivers/chromedriver/linux64/149.0.7827.155/chromedriver-linux64/chromedriver"
CHROME_PROFILE = "/home/shrridharshan/.shrri/chrome_profile"

def parse_whatsapp(message: str):
    phone_match = re.search(r"to\s+(\+?\d[\d\s\-]{7,13}\d)", message, re.IGNORECASE)
    if not phone_match:
        return None, "GAP: no phone number found."
    phone = re.sub(r"[\s\-]", "", phone_match.group(1))
    if not phone.startswith("+"):
        phone = "+91" + phone
    text = ""
    for marker in [" saying ", " message ", " that ", " body "]:
        idx = message.lower().find(marker)
        if idx != -1:
            text = message[idx + len(marker):].strip()
            break
    if not text:
        return None, "GAP: no message text found."
    return (phone, text), None

def _find_contact_phone(name: str) -> str:
    """Search WhatsApp Web for a contact name and return their phone number."""
    # We can't easily get phone from name without scraping contacts
    # So we return None and let the send flow use name-based URL instead
    return None

def send_by_name(name: str, text: str) -> str:
    """Send WhatsApp message by contact name using wa.me search."""
    import subprocess, urllib.parse, time
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    CHROMEDRIVER = "/home/shrridharshan/.wdm/drivers/chromedriver/linux64/149.0.7827.155/chromedriver-linux64/chromedriver"
    CHROME_PROFILE = "/home/shrridharshan/.shrri/chrome_profile"

    try:
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

        # Search for contact
        search = driver.find_element(By.XPATH, "//*[@aria-label='Search or start a new chat']")
        search.click()
        search.send_keys(name)
        time.sleep(2)

        # Wait for search results and click matching contact
        time.sleep(3)
        matched_name = name
        clicked = False

        # Try clicking span with title containing the name
        candidates = driver.find_elements(By.XPATH, "//span[@title]")
        for c in candidates:
            title = c.get_attribute("title") or ""
            if name.lower() in title.lower() and len(title) < 60:
                matched_name = title
                try:
                    c.click()
                    clicked = True
                    break
                except Exception:
                    # Try clicking parent
                    try:
                        driver.execute_script("arguments[0].click();", c)
                        clicked = True
                        break
                    except Exception:
                        continue

        if not clicked:
            driver.quit()
            return "GAP: no contact found matching '" + name + "'. Check the exact name saved in your phone."
        time.sleep(3)

        # Type message
        msg_box = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[@contenteditable='true' and @data-tab='10']")
        ))
        msg_box.click()
        msg_box.send_keys(text)
        time.sleep(1)

        # Click send button
        send_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[@aria-label='Send']")
        ))
        send_btn.click()
        time.sleep(2)
        driver.quit()
        return "Message sent to " + matched_name + ": \"" + text + "\""
    except Exception as e:
        driver.quit()
        return "GAP: send by name failed — " + str(e)

def send_whatsapp_now(phone: str, text: str) -> str:
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        options = Options()
        options.add_argument(f"--user-data-dir={CHROME_PROFILE}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-first-run")
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(service=Service(CHROMEDRIVER), options=options)

        encoded = urllib.parse.quote(text)
        url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded}"
        driver.get(url)

        print("SHRRI: Waiting for WhatsApp to load (up to 30s)...")
        wait = WebDriverWait(driver, 60)
        send_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[@aria-label=\'Send\']")
        ))
        time.sleep(2)
        send_btn.click()
        time.sleep(3)
        driver.quit()
        return f"Message sent to {phone}: \"{text}\""
    except Exception as e:
        return f"GAP: WhatsApp failed — {e}"

def send_whatsapp(message: str) -> str:
    result, err = parse_whatsapp(message)
    if err:
        # No phone number — try name-based search
        name_match = None
        for pat in [
            r"send\s+(?:a\s+)?message\s+to\s+([a-zA-Z][a-zA-Z\s]{1,30}?)\s+(?:saying|that|:)",
            r"send\s+(?:this\s+)?to\s+([a-zA-Z][a-zA-Z\s]{1,30}?)\s+(?:in|on|via)",
            r"message\s+to\s+([a-zA-Z][a-zA-Z\s]{1,30}?)\s+(?:saying|that)",
            r"(?:to|message)\s+([a-zA-Z][a-zA-Z\s]{1,30}?)\s+(?:saying|that|:)",
        ]:
            name_match = re.search(pat, message, re.IGNORECASE)
            if name_match:
                break
        if name_match:
            name = name_match.group(1).strip()
            text = ""
            for marker in [" saying ", " that ", " message "]:
                idx = message.lower().find(marker)
                if idx != -1:
                    text = message[idx + len(marker):].strip()
                    break
            if text:
                return "WHATSAPP_NAME_PENDING|" + name + "|" + text
        return err
    phone, text = result
    return "WHATSAPP_PENDING|" + phone + "|" + text
