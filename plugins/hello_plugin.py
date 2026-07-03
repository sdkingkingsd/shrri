"""
Example plugin — hello_plugin
"""
NAME = "hello_plugin"
VERSION = "1.0.0"
DESCRIPTION = "Example plugin that greets the user"


def run(input_text: str, context: dict = None) -> str:
    name = context.get("user", "world") if context else "world"
    return f"Hello, {name}! You said: {input_text}"
