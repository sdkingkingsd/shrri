"""
google_translit_tamil.py - Converts English words to natural Tamil script
using Google's transliteration backend (same engine behind Gboard/Google
Input Tools). Falls back to leaving the word as English if the lookup
fails (e.g. no internet) or returns nothing.
"""
import re
from google.transliteration import transliterate_word

_OVERRIDES = {
    "shrri": "ஷ்ரீ",
}

_CACHE = {}


def english_word_to_tamil(word: str) -> str:
    clean = re.sub(r"[^a-zA-Z']", "", word)
    if not clean:
        return word
    key = clean.lower()
    if key in _OVERRIDES:
        return _OVERRIDES[key]
    if key in _CACHE:
        return _CACHE[key]
    try:
        suggestions = transliterate_word(clean, lang_code="ta")
        result = suggestions[0] if suggestions else word
    except Exception as e:
        print(f"[google_translit] lookup failed for '{clean}': {e}")
        result = word
    _CACHE[key] = result
    return result


def convert_text_to_tamil(text: str) -> str:
    def repl(match):
        return english_word_to_tamil(match.group(0))
    return re.sub(r"[A-Za-z']+", repl, text)


if __name__ == "__main__":
    tests = [
        "Hello sir, how are you doing today?",
        "I am SHRRI, your personal assistant.",
        "You have two meetings scheduled this afternoon.",
        "Good morning, what is the weather like today?",
    ]
    for t in tests:
        print(t)
        print(" -> " + convert_text_to_tamil(t))
        print()
