"""
SHRRI — Test all providers with a live chat call.
Run from ~/shrri
"""
from engine.key_manager import KeyManager
from engine.providers import GroqProvider, CerebrasProvider, NvidiaProvider, OllamaProvider
from openai import OpenAI

km = KeyManager()

def test(name, fn):
    print(f"\n{'='*50}")
    print(f"  Testing: {name}")
    print(f"{'='*50}")
    try:
        fn()
    except Exception as e:
        print(f"  ❌ FAILED: {e}")

def test_groq():
    key, key_id = km.get_best_key("groq")
    model = km.get_model("groq")
    print(f"  key: {key_id}, model: {model}")
    p = GroqProvider(key)
    r = p.chat("Say hello in one sentence", model)
    print(f"  ✅ Response: {r}")
    km.mark_used(key_id)

def test_cerebras():
    key, key_id = km.get_best_key("cerebras")
    model = km.get_model("cerebras")
    print(f"  key: {key_id}, model: {model}")
    p = CerebrasProvider(key)
    r = p.chat("Say hello in one sentence", model)
    print(f"  ✅ Response: {r}")
    km.mark_used(key_id)

def test_nvidia():
    key, key_id = km.get_best_key("nvidia")
    model = km.get_model("nvidia")
    base_url = km.get_base_url("nvidia")
    print(f"  key: {key_id}, model: {model}")
    p = NvidiaProvider(key, base_url)
    r = p.chat("Say hello in one sentence", model)
    print(f"  ✅ Response: {r}")
    km.mark_used(key_id)

def test_openrouter():
    key, key_id = km.get_best_key("openrouter")
    model = km.get_model("openrouter")
    print(f"  key: {key_id}, model: {model}")
    client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1", max_retries=0)
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say hello in one sentence"}],
        max_tokens=200
    )
    print(f"  ✅ Response: {r.choices[0].message.content}")
    km.mark_used(key_id)

def test_google():
    key, key_id = km.get_best_key("google")
    model = km.get_model("google").replace("models/", "")
    print(f"  key: {key_id}, model: {model}")
    client = OpenAI(
        api_key=key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        max_retries=0
    )
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say hello in one sentence"}],
        max_tokens=200
    )
    print(f"  ✅ Response: {r.choices[0].message.content}")
    km.mark_used(key_id)

def test_nara():
    key, key_id = km.get_best_key("nara")
    model = km.get_model("nara")
    base_url = km.get_base_url("nara")
    print(f"  key: {key_id}, model: {model}")
    client = OpenAI(api_key=key, base_url=base_url, max_retries=0)
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say hello in one sentence"}],
        max_tokens=200
    )
    print(f"  ✅ Response: {r.choices[0].message.content}")
    km.mark_used(key_id)

test("Groq", test_groq)
test("Cerebras", test_cerebras)
test("Nvidia", test_nvidia)
test("OpenRouter", test_openrouter)
test("Google", test_google)
test("Nara", test_nara)

print(f"\n{'='*50}")
print("  Done testing all providers.")
print(f"{'='*50}")
