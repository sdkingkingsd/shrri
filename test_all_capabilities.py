import sys
sys.path.insert(0, '/home/shrridharshan/shrri')
from engine.router import Router
from config.capability_map import CAPABILITIES

r = Router()

TEST_PROMPTS = {
    "conversation": "Say hi in one sentence",
    "reasoning": "If a train travels 60km in 1hr, how far in 2.5hr?",
    "coding": "Write a python one-liner to reverse a list",
    "debugging": "Find the bug: def add(a,b): return a-b",
    "writing": "Write a 1-sentence tagline for a coffee shop",
    "summarize": "Summarize: The cat sat on the mat and slept all day.",
    "translate": "Translate 'good morning' to Tamil",
    "tamil": "தமிழில் ஒரு வரி எழுது",
    "vision": "hello",  # text-only test, vision models should still answer text
    "ocr": "hello",
    "document": "hello",
    "math": "What is 17 * 23?",
    "embeddings": "hello",
    "tool_calling": "hello",
    "medical": "What are common symptoms of the flu?",
    "finance": "What is compound interest?",
}

results = {}
for cap in CAPABILITIES:
    prompt = TEST_PROMPTS.get(cap, "hello")
    print(f"\n{'='*50}\nTesting: {cap}\n{'='*50}")
    try:
        resp = r.chat(prompt, capability=cap, web_search=False)
        ok = bool(resp) and "ERROR" not in resp[:20]
        results[cap] = "✅ OK" if ok else "⚠️ EMPTY/ERROR"
        print(resp[:200] if resp else "NO RESPONSE")
    except Exception as e:
        results[cap] = f"❌ FAILED: {e}"
        print(f"FAILED: {e}")

print(f"\n\n{'='*50}\nSUMMARY\n{'='*50}")
for cap, status in results.items():
    print(f"{cap:20s} {status}")
