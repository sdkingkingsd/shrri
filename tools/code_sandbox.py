"""
code_sandbox.py - Run arbitrary Python code safely inside an isolated,
network-less, file-isolated Docker container with strict resource limits.
"""
import subprocess
import tempfile
import os

TIMEOUT_SECONDS = 10
MEMORY_LIMIT = "256m"
CPU_LIMIT = "0.5"
PIDS_LIMIT = "50"
DOCKER_IMAGE = "python:3.12-slim"

def run_code(code: str) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        script_path = f.name

    os.chmod(script_path, 0o644)

    try:
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--network", "none",
                "--memory=" + MEMORY_LIMIT,
                "--cpus=" + CPU_LIMIT,
                "--pids-limit=" + PIDS_LIMIT,
                "--security-opt", "no-new-privileges",
                "--cap-drop", "ALL",
                "--tmpfs", "/tmp:rw,size=64m",
                "-v", script_path + ":/sandbox_script.py:ro",
                DOCKER_IMAGE,
                "timeout", str(TIMEOUT_SECONDS),
                "python3", "/sandbox_script.py",
            ],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS + 5,
        )
        output = (result.stdout or "") + (result.stderr or "")
        if not output.strip():
            output = "(no output)"
        return output[:3000]
    except subprocess.TimeoutExpired:
        return "Code execution timed out (outer limit)."
    except Exception as e:
        return "Sandbox error: " + str(e)
    finally:
        try:
            os.remove(script_path)
        except Exception:
            pass
