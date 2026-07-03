"""
Native desktop window for SHRRI webui.
Starts the FastAPI backend in a background thread, then opens
a native OS window pointing at it — no browser tab needed.
"""
import threading
import time
import webview
import uvicorn

# Adjust this import to match how shrri_webui.sh actually starts your app
from webui.api.main import app

def run_backend():
    uvicorn.run(app, host="127.0.0.1", port=7788, log_level="warning")

if __name__ == "__main__":
    t = threading.Thread(target=run_backend, daemon=True)
    t.start()
    time.sleep(1.5)  # give uvicorn a moment to bind the port

    webview.create_window(
        "SHRRI AI OS",
        "http://127.0.0.1:7788",
        width=1400,
        height=900,
        min_size=(900, 600),
        background_color="#11111b",
    )
    webview.start()
