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
        return msg.content or getattr(msg, 'reasoning_content', None) or "No response"


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
