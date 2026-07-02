"""
Language Detection Engine — SHRRI AI OS v2

Detects the language of incoming text so the Context Builder / prompt
can adapt (e.g. respond in Tamil-script Tanglish vs plain English).

Uses langdetect (lightweight, CPU-friendly) as the base signal, plus a
simple heuristic for Tanglish (Tamil words typed in Latin script) since
langdetect alone tends to misclassify romanized Tamil as English/Indonesian.
"""

from langdetect import detect, LangDetectException

# Common Tanglish/Tamil-in-Latin-script markers — cheap heuristic, not
# exhaustive. Extend this list as you notice misclassifications.
TANGLISH_MARKERS = {
    "da", "pa", "sir", "enna", "epdi", "irukku", "vanthu", "poitu",
    "seri", "illa", "vera", "level", "mokka", "semma", "நீங்கள்",
}


class LanguageDetectionEngine:
    def detect(self, text: str) -> dict:
        text_lower = text.lower()
        words = set(text_lower.split())

        tanglish_hits = words & TANGLISH_MARKERS
        has_tamil_script = any("\u0B80" <= ch <= "\u0BFF" for ch in text)

        if has_tamil_script:
            base_lang = "ta"
            confidence = "high"
        elif tanglish_hits:
            base_lang = "ta-tanglish"
            confidence = "heuristic"
        else:
            try:
                base_lang = detect(text)
                confidence = "model"
            except LangDetectException:
                base_lang = "unknown"
                confidence = "none"

        return {
            "language": base_lang,
            "confidence": confidence,
            "tanglish_markers_found": list(tanglish_hits),
        }
