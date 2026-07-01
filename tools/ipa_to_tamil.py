"""
ipa_to_tamil.py - Converts English text to Tamil script via real IPA
pronunciation (CMU dictionary, through eng_to_ipa), not spelling guesses.
This is what actually makes Piper's Tamil voice pronounce English clearly.
"""
import re
import eng_to_ipa as ipa

_VOWEL_STANDALONE = {
    "a": "அ", "aa": "ஆ", "i": "இ", "ii": "ஈ", "u": "உ", "uu": "ஊ",
    "e": "எ", "ee": "ஏ", "ai": "ஐ", "o": "ஒ", "oo": "ஓ", "au": "ஔ",
}
_VOWEL_SIGN = {
    "a": "", "aa": "ா", "i": "ி", "ii": "ீ", "u": "ு", "uu": "ூ",
    "e": "ெ", "ee": "ே", "ai": "ை", "o": "ொ", "oo": "ோ", "au": "ௌ",
}
_CONSONANT = {
    "p": "ப", "b": "ப", "t": "ட", "d": "ட", "k": "க", "g": "க",
    "ch": "ச", "j": "ஜ", "f": "ஃப", "v": "வ", "th": "த", "dh": "த",
    "s": "ஸ", "z": "ஸ", "sh": "ஷ", "zh": "ஜ", "h": "ஹ", "m": "ம",
    "n": "ன", "ng": "ங", "l": "ல", "r": "ர", "y": "ய", "w": "வ",
}
_IPA_VOWELS = [
    ("oʊ", "oo"), ("aɪ", "ai"), ("aʊ", "au"), ("ɔɪ", "ai"),
    ("ɝ", "a"), ("ɜ", "a"), ("ɚ", "a"),
    ("iː", "ii"), ("i", "ii"), ("ɪ", "i"),
    ("ɛ", "e"), ("eɪ", "ee"), ("e", "ee"),
    ("æ", "a"), ("ɑː", "aa"), ("ɑ", "aa"), ("ɒ", "aa"),
    ("ɔː", "oo"), ("ɔ", "oo"), ("ʌ", "a"), ("ə", "a"),
    ("uː", "uu"), ("u", "uu"), ("ʊ", "u"),
]
_IPA_CONSONANTS = [
    ("tʃ", "ch"), ("dʒ", "j"), ("ʧ", "ch"), ("ʤ", "j"), ("ʃ", "sh"), ("ʒ", "zh"),
    ("θ", "th"), ("ð", "dh"), ("ŋ", "ng"),
    ("p", "p"), ("b", "b"), ("t", "t"), ("d", "d"), ("k", "k"), ("g", "g"),
    ("f", "f"), ("v", "v"), ("s", "s"), ("z", "z"), ("h", "h"),
    ("m", "m"), ("n", "n"), ("l", "l"), ("r", "r"), ("j", "y"), ("w", "w"),
]
_ALL_SYMBOLS = sorted(
    [(sym, ("V", key)) for sym, key in _IPA_VOWELS] +
    [(sym, ("C", key)) for sym, key in _IPA_CONSONANTS],
    key=lambda x: -len(x[0])
)

_OVERRIDES = {
    "shrri": "ஷ்ரீ",
}


def _tokenize_ipa(ipa_word: str):
    s = ipa_word.replace("ˈ", "").replace("ˌ", "").replace("ː", "")
    tokens = []
    i = 0
    while i < len(s):
        matched = False
        for sym, val in _ALL_SYMBOLS:
            if s.startswith(sym, i):
                tokens.append(val)
                i += len(sym)
                matched = True
                break
        if not matched:
            i += 1
    return tokens


def _tokens_to_tamil(tokens) -> str:
    out = []
    i = 0
    n = len(tokens)
    while i < n:
        kind, key = tokens[i]
        if kind == "C":
            base = _CONSONANT.get(key, "")
            if not base:
                i += 1
                continue
            if i + 1 < n and tokens[i + 1][0] == "V":
                vkind, vkey = tokens[i + 1]
                out.append(base + _VOWEL_SIGN.get(vkey, ""))
                i += 2
            else:
                out.append(base + "்")
                i += 1
        else:
            out.append(_VOWEL_STANDALONE.get(key, ""))
            i += 1
    return "".join(out)


def english_word_to_tamil(word: str) -> str:
    clean = re.sub(r"[^a-zA-Z']", "", word)
    if not clean:
        return word
    if clean.lower() in _OVERRIDES:
        return _OVERRIDES[clean.lower()]
    ipa_str = ipa.convert(clean.lower())
    if "*" in ipa_str or not ipa_str.strip():
        return word
    ipa_str = ipa_str.replace(" ", "")
    tokens = _tokenize_ipa(ipa_str)
    tamil = _tokens_to_tamil(tokens)
    return tamil if tamil else word


def convert_text_to_tamil(text: str) -> str:
    def repl(match):
        return english_word_to_tamil(match.group(0))
    return re.sub(r"[A-Za-z']+", repl, text)


if __name__ == "__main__":
    tests = [
        "Hello sir, how are you doing today?",
        "I am SHRRI, your personal assistant.",
        "You have two meetings scheduled this afternoon.",
        "Naa SHRRI da, weather check pannalama?",
        "Good morning, what is the weather like today?",
    ]
    for t in tests:
        print(t)
        print(" -> " + convert_text_to_tamil(t))
        print()
