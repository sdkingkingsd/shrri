import requests
from openai import OpenAI


class GroqProvider:
    def __init__(self, api_key):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            max_retries=0
        )

    def chat(self, message, model, history=None, system=None):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=4096
        )
        return response.choices[0].message.content


class CerebrasProvider:
    def __init__(self, api_key):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.cerebras.ai/v1",
            max_retries=0
        )

    def chat(self, message, model, history=None, system=None):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1024
        )
        msg = response.choices[0].message
        text = msg.content if msg.content and msg.content.strip() else None
        text = text or getattr(msg, 'reasoning_content', None)
        return text.strip() if text else "No response"


class NvidiaProvider:
    def __init__(self, api_key, base_url):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=0
        )

    def chat(self, message, model, history=None, system=None):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=4096
        )
        return response.choices[0].message.content


class OllamaProvider:
    def __init__(self, base_url):
        self.base_url = base_url

    def chat(self, message, model, history=None, system=None):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False
            },
            timeout=120
        )
        return response.json()["message"]["content"]


class TempLLMProvider:
    """ChatGPT via templlm browser automation — rate limit fallback."""
    def __init__(self):
        self.base_url = "http://localhost:8000"

    def is_available(self):
        try:
            import requests
            r = requests.get(f"{self.base_url}/health", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def chat(self, prompt, **kwargs):
        try:
            import requests
            r = requests.post(
                f"{self.base_url}/ask",
                json={"prompt": prompt},
                timeout=60
            )
            data = r.json()
            response = data.get("response", "")
            if not response or "Error" in response:
                raise Exception(f"TempLLM bad response: {response}")
            # Retry once if response looks corrupted (mashed/repeated fragments)
            import re
            words = response.split()
            if len(words) > 5:
                # crude corruption check: same short word-fragment repeated back to back
                suspicious = any(words[i] == words[i+1] for i in range(len(words)-1) if len(words[i]) <= 3)
                garbled = bool(re.search(r"[a-z][A-Z][a-z]+[A-Z]", response))  # camelCase mashups like "capiFrance"
                if suspicious or garbled:
                    r2 = requests.post(f"{self.base_url}/ask", json={"prompt": prompt}, timeout=60)
                    response2 = r2.json().get("response", "")
                    if response2 and len(response2) > 10:
                        response = response2
            return response.strip()
        except Exception as e:
            raise Exception(f"TempLLM error: {e}")
