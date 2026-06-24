import sys
sys.path.insert(0, '/home/shrridharshan/shrri')

import yaml
import os
import time
from openai import OpenAI
import requests

KEYS_FILE = os.path.expanduser("~/.shrri/keys.yaml")

def load_keys():
    with open(KEYS_FILE, "r") as f:
        return yaml.safe_load(f)

def ask_groq(api_key, key_id):
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "who are you? answer in one line."}],
        max_tokens=50
    )
    return r.choices[0].message.content

def ask_cerebras(api_key, key_id):
    client = OpenAI(api_key=api_key, base_url="https://api.cerebras.ai/v1")
    r = client.chat.completions.create(
        model="zai-glm-4.7",
        messages=[{"role": "user", "content": "who are you? answer in one line."}],
        max_tokens=1024
    )
    msg = r.choices[0].message
    return msg.content or getattr(msg, 'reasoning_content', None) or "No response"

def ask_nvidia(api_key, key_id):
    client = OpenAI(api_key=api_key, base_url="https://integrate.api.nvidia.com/v1")
    r = client.chat.completions.create(
        model="meta/llama-3.1-8b-instruct",
        messages=[{"role": "user", "content": "who are you? answer in one line."}],
        max_tokens=50
    )
    return r.choices[0].message.content

def ask_ollama():
    r = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "qwen2.5:3b",
            "messages": [{"role": "user", "content": "who are you? answer in one line."}],
            "stream": False
        },
        timeout=60
    )
    return r.json()["message"]["content"]

def run():
    config = load_keys()
    providers = config["providers"]

    print("\n" + "="*60)
    print("   SHRRI — WHO ARE YOU? (All 31 Keys)")
    print("="*60)

    testers = {
        "groq": ask_groq,
        "cerebras": ask_cerebras,
        "nvidia": ask_nvidia,
    }

    for provider_name, fn in testers.items():
        print(f"\n{'='*20} {provider_name.upper()} {'='*20}")
        keys = providers[provider_name]["keys"]
        for key_entry in keys:
            key_id = key_entry["id"]
            api_key = key_entry["key"]
            if api_key.startswith("YOUR_"):
                continue
            try:
                start = time.time()
                response = fn(api_key, key_id)
                elapsed = round(time.time() - start, 2)
                print(f"\n[{key_id}] ({elapsed}s)")
                print(f"  → {response}")
            except Exception as e:
                print(f"\n[{key_id}] ❌ {str(e)[:60]}")
            time.sleep(0.3)

    print(f"\n{'='*20} OLLAMA {'='*20}")
    try:
        start = time.time()
        response = ask_ollama()
        elapsed = round(time.time() - start, 2)
        print(f"\n[ollama_local] ({elapsed}s)")
        print(f"  → {response}")
    except Exception as e:
        print(f"\n[ollama_local] ❌ {str(e)[:60]}")

    print("\n" + "="*60)
    print("Done!")
    print("="*60)

if __name__ == "__main__":
    run()
