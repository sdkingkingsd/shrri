import tiktoken

# cl100k_base is a close-enough approximation for most modern LLMs
# (exact tokenizer differs per provider, but this gives a realistic estimate)
_encoder = tiktoken.get_encoding("cl100k_base")

def count_tokens(text):
    if not text:
        return 0
    return len(_encoder.encode(text))

def count_messages(messages):
    """messages = list of {'role':..., 'content':...} dicts"""
    total = 0
    for m in messages:
        total += count_tokens(m.get("content", ""))
    return total
