"""Python executor — runs safe Python code snippets for math, data analysis."""
import subprocess, tempfile, os, re

BLOCKED = ["import os", "import sys", "import subprocess", "open(", "__import__",
           "eval(", "exec(", "shutil", "socket", "requests", "urllib"]

def run_python(message: str) -> str:
    try:
        # Extract code block if present
        code_match = re.search(r"```python\n(.+?)```", message, re.DOTALL)
        if code_match:
            code = code_match.group(1)
        else:
            # Generate simple math/analysis code from natural language
            return "GAP: provide code in ```python blocks```"

        # Safety check
        for blocked in BLOCKED:
            if blocked in code:
                return "GAP: unsafe code blocked — " + blocked

        # Write to temp file and run
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                         delete=False, dir="/tmp") as f:
            f.write(code)
            tmpfile = f.name

        result = subprocess.run(
            ["python3", tmpfile],
            capture_output=True, text=True, timeout=10
        )
        os.unlink(tmpfile)

        if result.returncode == 0:
            return result.stdout.strip() or "Code ran successfully (no output)."
        else:
            return "Error: " + result.stderr.strip()[:300]

    except subprocess.TimeoutExpired:
        return "GAP: code timed out after 10 seconds."
    except Exception as e:
        return "GAP: executor failed — " + str(e)
