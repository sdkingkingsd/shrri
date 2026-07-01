"""
eng_to_tamil_phonetic.py - Lightweight rule-based English -> Tamil script
phonetic converter, for feeding English words into the Piper Tamil voice
so it pronounces them correctly instead of reading raw Latin script.
Not a full linguistic transliterator - just good-enough word mapping for
everyday assistant vocabulary. Unmapped words are left as plain English
rather than mangled into garbled letter-by-letter Tamil.
"""
import re

_WORD_MAP = {
    "hello": "ஹலோ",
    "hi": "ஹாய்",
    "hey": "ஹே",
    "ok": "ஓகே",
    "okay": "ஓகே",
    "yes": "யெஸ்",
    "no": "நோ",
    "sir": "சார்",
    "weather": "வெதர்",
    "calendar": "காலெண்டர்",
    "reminder": "ரிமைண்டர்",
    "reminders": "ரிமைண்டர்ஸ்",
    "email": "ஈமெயில்",
    "emails": "ஈமெயில்ஸ்",
    "whatsapp": "வாட்ஸ்அப்",
    "message": "மெசேஜ்",
    "messages": "மெசேஜஸ்",
    "meeting": "மீட்டிங்",
    "meetings": "மீட்டிங்ஸ்",
    "today": "டுடே",
    "tomorrow": "டுமாரோ",
    "schedule": "ஷெட்யூல்",
    "scheduled": "ஷெட்யூல்ட்",
    "afternoon": "ஆஃப்டர்நூன்",
    "morning": "மார்னிங்",
    "evening": "ஈவினிங்",
    "night": "நைட்",
    "shrri": "ஷ்ரீ",
    "assistant": "அசிஸ்டென்ட்",
    "personal": "பர்சனல்",
}


def _phonetic_word(word: str) -> str:
    w = word.lower()
    if w in _WORD_MAP:
        return _WORD_MAP[w]
    return word


def convert_english_to_tamil_phonetic(text: str) -> str:
    """Replace mapped English words with Tamil-script phonetic equivalents.
    Unmapped English words, Tamil-script text, and punctuation pass through
    unchanged."""
    def repl(match):
        return _phonetic_word(match.group(0))
    return re.sub(r"[A-Za-z]+", repl, text)


if __name__ == "__main__":
    tests = [
        "Hello sir, how are you doing today?",
        "I am SHRRI, your personal assistant.",
        "You have two meetings scheduled this afternoon.",
        "Naa SHRRI da, weather check pannalama?",
    ]
    for t in tests:
        print(t, "->", convert_english_to_tamil_phonetic(t))
