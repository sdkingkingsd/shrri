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
        return err
    phone, text = result
    return f"WHATSAPP_PENDING|{phone}|{text}"
