import sys
import time
sys.path.insert(0, '/home/shrridharshan/shrri')

import yaml
import os
from openai import OpenAI
import requests

KEYS_FILE = os.path.expanduser("~/.shrri/keys.yaml")

def load_keys():
    with open(KEYS_FILE, "r") as f:
        return yaml.safe_load(f)

def test_groq(key_id, api_key):
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "say ok"}],
            max_tokens=5
        )
        return True, "OK"
    except Exception as e:
        return False, str(e)[:60]

def test_cerebras(key_id, api_key):
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.cerebras.ai/v1")
        response = client.chat.completions.create(
            model="gpt-oss-120b",
            messages=[{"role": "user", "content": "say ok"}],
            max_tokens=5
        )
        return True, "OK"
    except Exception as e:
        return False, str(e)[:60]

def test_nvidia(key_id, api_key):
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1"
        )
        response = client.chat.completions.create(
            model="meta/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": "say ok"}],
            max_tokens=5
        )
        return True, "OK"
    except Exception as e:
        return False, str(e)[:60]

def test_ollama():
    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "qwen2.5:3b",
                "messages": [{"role": "user", "content": "say ok"}],
                "stream": False
            },
            timeout=30
        )
        return True, "OK"
    except Exception as e:
        return False, str(e)[:60]

def run_tests():
    config = load_keys()
    providers = config["providers"]

    results = {}
    total = 0
    passed = 0

    print("\n" + "="*55)
    print("       SHRRI API KEY TESTER")
    print("="*55)

    testers = {
        "groq": test_groq,
        "cerebras": test_cerebras,
        "nvidia": test_nvidia,
    }

    for provider_name, test_fn in testers.items():
        print(f"\n[{provider_name.upper()}]")
        results[provider_name] = []
        keys = providers[provider_name]["keys"]

        for key_entry in keys:
            key_id = key_entry["id"]
            api_key = key_entry["key"]

            if api_key.startswith("YOUR_"):
                print(f"  {key_id:<15} ⚠️  NOT SET")
                results[provider_name].append((key_id, False, "Not set"))
                total += 1
                continue

            total += 1
            ok, msg = test_fn(key_id, api_key)
            if ok:
                passed += 1
                print(f"  {key_id:<15} ✅ WORKS")
            else:
                print(f"  {key_id:<15} ❌ FAILED — {msg}")
            results[provider_name].append((key_id, ok, msg))
            time.sleep(0.5)

    # Test Ollama separately
    print(f"\n[OLLAMA]")
    ok, msg = test_ollama()
    total += 1
    if ok:
        passed += 1
        print(f"  ollama_local    ✅ WORKS")
    else:
        print(f"  ollama_local    ❌ FAILED — {msg}")

    print("\n" + "="*55)
    print(f"  TOTAL: {passed}/{total} keys working")
    print("="*55 + "\n")

if __name__ == "__main__":
    run_tests()
