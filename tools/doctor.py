import os, sys, time
sys.path.insert(0, os.path.expanduser("~/shrri"))

def check(label, fn):
    try:
        result = fn()
        if result is True:
            print(f"  ✅ {label}")
            return True
        else:
            print(f"  ❌ {label}: {result}")
            return False
    except Exception as e:
        print(f"  ❌ {label}: {e}")
        return False

def run_doctor():
    print("\n🩺 SHRRI Doctor — System Health Check")
    print("=" * 45)
    passed = 0
    total = 0

    print("\n[Network]")
    def check_internet():
        import urllib.request
        urllib.request.urlopen("https://www.google.com", timeout=5)
        return True
    total += 1
    if check("Internet connection", check_internet): passed += 1

    print("\n[AI Providers]")
    from engine.key_manager import KeyManager
    km = KeyManager()
    for provider in ["groq", "cerebras", "nvidia", "ollama"]:
        total += 1
        def check_provider(p=provider):
            if p == "ollama":
                import urllib.request
                urllib.request.urlopen("http://localhost:11434", timeout=3)
                return True
            key, _ = km.get_best_key(p)
            if not key or key.startswith("YOUR_"):
                return "no API key"
            return True
        if check(f"Provider: {provider}", check_provider): passed += 1

    print("\n[Memory]")
    total += 1
    def check_memory():
        from engine.memory import Memory
        m = Memory()
        m.conn.execute("SELECT count(*) FROM facts").fetchone()
        return True
    if check("Memory database", check_memory): passed += 1

    print("\n[Gmail]")
    total += 1
    def check_gmail():
        token = os.path.expanduser("~/.shrri/gmail_token.json")
        creds = os.path.expanduser("~/.shrri/gmail_credentials.json")
        if not os.path.exists(token): return "token missing"
        if not os.path.exists(creds): return "credentials missing"
        return True
    if check("Gmail auth", check_gmail): passed += 1

    print("\n[WhatsApp]")
    total += 1
    def check_whatsapp():
        profile = os.path.expanduser("~/.shrri/chrome_profile")
        if not os.path.exists(profile): return "Chrome profile missing"
        chromedriver = "/home/shrridharshan/.wdm/drivers/chromedriver/linux64/149.0.7827.155/chromedriver-linux64/chromedriver"
        if not os.path.exists(chromedriver): return "ChromeDriver missing"
        return True
    if check("WhatsApp (Chrome profile)", check_whatsapp): passed += 1

    print("\n[Voice]")
    total += 1
    def check_tts():
        try:
            import edge_tts
            return True
        except ImportError:
            try:
                from gtts import gTTS
                return True
            except ImportError:
                return "edge_tts and gtts both missing"
    if check("Voice TTS (edge-tts)", check_tts): passed += 1

    print("\n[Scheduler]")
    total += 1
    def check_scheduler():
        import subprocess
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        shrri_jobs = [l for l in result.stdout.splitlines() if "run_automation" in l]
        return True if shrri_jobs else "no SHRRI cron jobs found"
    if check("Scheduler (cron jobs)", check_scheduler): passed += 1

    print("\n[System]")
    total += 1
    def check_disk():
        import shutil
        free_gb = shutil.disk_usage(os.path.expanduser("~")).free / (1024**3)
        if free_gb < 1: return f"only {free_gb:.1f}GB free"
        return True
    if check("Disk space", check_disk): passed += 1

    total += 1
    def check_schedules():
        import json
        path = os.path.expanduser("~/.shrri/schedules.json")
        if not os.path.exists(path): return "no schedules yet"
        jobs = json.load(open(path))
        return True if jobs else "empty"
    if check("Schedules file", check_schedules): passed += 1

    print("\n" + "=" * 45)
    emoji = "✅" if passed == total else "⚠️" if passed >= total * 0.7 else "❌"
    print(f"{emoji} {passed}/{total} checks passed\n")
    if passed == total:
        print("SHRRI is fully healthy!\n")
    else:
        print(f"{total - passed} issue(s) found. Fix them above and run shrri doctor again.\n")

if __name__ == "__main__":
    run_doctor()
