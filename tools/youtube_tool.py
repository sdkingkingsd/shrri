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

def _search_yt_url(query):
    import urllib.parse, urllib.request
    q = urllib.parse.quote(query)
    req = urllib.request.Request(
        "https://www.youtube.com/results?search_query=" + q,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    import re as _re
    html = urllib.request.urlopen(req, timeout=10).read().decode()
    # Anchor to videoRenderer blocks — these are real search results,
    # in the order YouTube actually displays them. A bare "videoId" search
    # picks up ads/sidebar/config junk that appears earlier in the page.
    m = _re.search(r'"videoRenderer":\{"videoId":"([a-zA-Z0-9_-]{11})"', html)
    if not m:
        # Fallback: some page variants nest videoId right after videoRenderer
        # but not as the literal first key — search within a window after
        # the first "videoRenderer" occurrence instead of the whole page.
        vr = html.find('"videoRenderer"')
        if vr != -1:
            window = html[vr:vr+500]
            m2 = _re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', window)
            if m2:
                return "https://www.youtube.com/watch?v=" + m2.group(1)
        return None
    return "https://www.youtube.com/watch?v=" + m.group(1)

def summarize_youtube(message: str) -> str:
    try:
        # Extract URL
        url_match = re.search(r"https?://[\S]+", message)
        if url_match:
            url = url_match.group()
        else:
            query = message
            for prefix in ["summarize ", "summary of ", "summarise "]:
                if query.lower().startswith(prefix):
                    query = query[len(prefix):]
                    break
            url = _search_yt_url(query)
            if not url:
                return "GAP: could not find that video on YouTube."
            print("SHRRI: Found — " + url)

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
