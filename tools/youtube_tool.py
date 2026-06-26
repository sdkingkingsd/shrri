"""YouTube summarizer — fetches transcript and summarizes via LLM."""
import re

def extract_video_id(url: str) -> str:
    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"embed/([a-zA-Z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

def summarize_youtube(message: str) -> str:
    try:
        # Extract URL
        url_match = re.search(r"https?://[\S]+", message)
        if not url_match:
            return "GAP: no YouTube URL found. Try: summarize youtube.com/watch?v=..."
        url = url_match.group()

        video_id = extract_video_id(url)
        if not video_id:
            return f"GAP: could not extract video ID from {url}"

        # Fetch transcript
        from youtube_transcript_api import YouTubeTranscriptApi
        try:
            ytt = YouTubeTranscriptApi()
            fetched = ytt.fetch(video_id)
            transcript = [{"text": s.text} for s in fetched]
        except Exception as te:
            return f"GAP: could not fetch transcript — {te}"

        # Join transcript text
        full_text = " ".join([t["text"] for t in transcript])

        # Truncate to ~3000 words for LLM
        words = full_text.split()
        if len(words) > 3000:
            full_text = " ".join(words[:3000]) + "... [truncated]"

        # Summarize via LLM (returns to engine for processing)
        return f"YOUTUBE_SUMMARIZE|{video_id}|{full_text}"

    except Exception as e:
        return f"GAP: YouTube summarizer failed — {e}"
