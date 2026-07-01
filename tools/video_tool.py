"""
video_tool.py - Video analysis using Gemini 2.5 Flash (free tier).
Send a video file path and a question, get an answer back.
"""
import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/shrri"))


def analyze_video(video_path: str, question: str = "Summarize what is happening in this video.") -> str:
    """Upload a video to Gemini and ask a question about it."""
    try:
        from google import genai
        from engine.key_manager import KeyManager

        km = KeyManager()
        api_key, key_id = km.get_best_key("gemini")
        if not api_key:
            return "GAP: no Gemini API key found."

        if not os.path.exists(video_path):
            return f"GAP: video file not found — {video_path}"

        client = genai.Client(api_key=api_key)

        print(f"[video_tool] Uploading {os.path.basename(video_path)}...")
        with open(video_path, "rb") as f:
            uploaded = client.files.upload(
                file=f,
                config={"mime_type": _get_mime(video_path)}
            )

        # Wait for file to be processed
        print("[video_tool] Waiting for Gemini to process video...")
        for _ in range(30):
            file_info = client.files.get(name=uploaded.name)
            if file_info.state.name == "ACTIVE":
                break
            time.sleep(2)
        else:
            return "GAP: Gemini took too long to process the video."

        print("[video_tool] Analyzing...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[uploaded, question]
        )

        # Cleanup uploaded file
        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass

        return response.text

    except Exception as e:
        return f"GAP: video analysis failed — {e}"


def _get_mime(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return {
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
        ".3gp": "video/3gpp",
    }.get(ext, "video/mp4")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 video_tool.py <video_path> [question]")
        sys.exit(1)
    path = sys.argv[1]
    q = sys.argv[2] if len(sys.argv) > 2 else "Summarize what is happening in this video."
    print(analyze_video(path, q))
