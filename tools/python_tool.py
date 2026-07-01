"""Python executor - runs Python code snippets inside an isolated Docker sandbox."""
import re

def run_python(message: str) -> str:
    code_match = re.search(r"```python\n(.+?)```", message, re.DOTALL)
    if not code_match:
        return "GAP: provide code in python code blocks"
    code = code_match.group(1)
    from tools.code_sandbox import run_code
    return run_code(code)
