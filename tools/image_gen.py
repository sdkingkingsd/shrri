"""Image generation tool - uses Pollinations.ai (free, no API key needed)."""
import urllib.request
import urllib.parse
import os
import time

OUTPUT_DIR = os.path.expanduser("~/.shrri/generated_images")

def generate_image(prompt: str) -> str:
    """Generate an image from a text prompt and save it locally.
    Returns the path to the saved image, or a GAP: error message."""
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        clean_prompt = prompt.strip()
        if not clean_prompt:
            return "GAP: no prompt provided for image generation."

        encoded = urllib.parse.quote(clean_prompt)
        seed = int(time.time())
        url = "https://image.pollinations.ai/prompt/" + encoded + "?width=1024&height=1024&seed=" + str(seed) + "&nologo=true"

        req = urllib.request.Request(url, headers={"User-Agent": "SHRRI/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            image_data = r.read()

        ts = time.strftime("%Y%m%d_%H%M%S")
        filename = "image_" + ts + ".jpg"
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(image_data)

        return "IMAGE_GENERATED|" + filepath
    except Exception as e:
        return "GAP: image generation failed - " + str(e)
