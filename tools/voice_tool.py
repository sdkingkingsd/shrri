"""Voice tool — Tanglish support, Indian female voice."""
import subprocess, tempfile, os, re
import speech_recognition as sr

def _split_tanglish(text):
    """Split text into Tamil and English chunks."""
    chunks = []
    current = ""
    current_lang = None
    for char in text:
        if "\u0B80" <= char <= "\u0BFF":
            lang = "ta"
        elif char.isascii():
            lang = "en"
        else:
            lang = current_lang or "en"
        if lang != current_lang and current.strip():
            chunks.append((current_lang or "en", current.strip()))
            current = char
            current_lang = lang
        else:
            current += char
            current_lang = lang
    if current.strip():
        chunks.append((current_lang or "en", current.strip()))
    return chunks

def speak(text: str):
    """Speak Tanglish — switches voice per chunk."""
    try:
        from gtts import gTTS
        text = text.replace("SHRRI", "Shree").replace("shrri", "Shree")
        text = re.sub(r"[*#`•]", "", text).strip()
        if not text:
            return

        chunks = _split_tanglish(text)

        for lang, chunk in chunks:
            if not chunk:
                continue
            tld = "co.in" if lang == "en" else "com"
            try:
                tts = gTTS(text=chunk, lang=lang, tld=tld, slow=False)
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir="/tmp") as f:
                    fname = f.name
                tts.save(fname)
                subprocess.run(["mpg123", "-q", fname],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                os.unlink(fname)
            except Exception:
                continue

    except Exception as e:
        subprocess.run(["espeak-ng", "-v", "en-us", text],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def listen(lang="en-IN") -> str:
    """Listen from mic — supports Tamil and English."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Shree: Listening...")
        r.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = r.listen(source, timeout=8, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            return ""
    # Try Tamil+English mixed recognition
    for lang_code in ["ta-IN", "en-IN"]:
        try:
            return r.recognize_google(audio, language=lang_code)
        except sr.UnknownValueError:
            continue
        except sr.RequestError as e:
            print(f"Speech error: {e}")
            return ""
    return ""
