"""
DynamicAgentFactory — SHRRI Phase 6G
Creates new agent types at runtime from a plain-English description.
"""
import os, re, logging, importlib.util
logger = logging.getLogger(__name__)
DYNAMIC_AGENTS_DIR = os.path.expanduser("~/.shrri/dynamic_agents")

AGENT_TEMPLATE = """
import logging
logger = logging.getLogger(__name__)
def run(payload: dict) -> str:
    prompt = payload.get("prompt", "")
{logic}
"""

def _generate_agent_code(name, description, router):
    gen_prompt = (
        f"Write a Python function body (8-space indent) for an agent called '{name}'.\n"
        f"Job: {description}\n"
        f"Rules: use only stdlib + prompt variable, import inside body, always return a string, no markdown.\n"
        f"Output ONLY the indented code lines, nothing else."
    )
    try:
        res = router.generate(gen_prompt, capability="code")
        if res.get("success") and res.get("text","").strip():
            raw = res["text"].strip()
            raw = re.sub(r"^```[a-z]*\n?","",raw,flags=re.M)
            raw = re.sub(r"\n?```$","",raw,flags=re.M)
            # Normalize indent: strip 4 spaces from every line that has 8+ spaces
            # Also fix bare imports (0-indent) mixed with 8-indent body — add 4 spaces
            lines = raw.split("\n")
            has_8indent = any(l.startswith("        ") for l in lines if l.strip())
            if has_8indent:
                fixed = []
                for l in lines:
                    if l.startswith("        "):
                        fixed.append(l[4:])  # 8->4
                    elif l.strip() and not l.startswith(" "):
                        fixed.append("    " + l)  # bare line -> 4-indent
                    else:
                        fixed.append(l)
                raw = "\n".join(fixed)
            return raw
    except Exception as e:
        logger.warning(f"[dynamic_agent] gen failed: {e}")
    logger.warning(f"[dynamic_agent] generation failed for '{name}', using stub")
    return '    return "stub: " + prompt'

def _syntax_check(code):
    import py_compile, tempfile
    with tempfile.NamedTemporaryFile(mode="w",suffix=".py",delete=False) as f:
        f.write(code); tmp=f.name
    try:
        py_compile.compile(tmp,doraise=True); return True,""
    except py_compile.PyCompileError as e:
        return False,str(e)
    finally:
        os.unlink(tmp)

def _save_agent(name, code):
    os.makedirs(DYNAMIC_AGENTS_DIR, exist_ok=True)
    path = os.path.join(DYNAMIC_AGENTS_DIR, f"{name}_agent.py")
    with open(path,"w") as f: f.write(code)
    return path

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(f"dynamic_agents.{name}_agent", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class DynamicAgentFactory:
    def __init__(self, router, manager):
        self.router = router
        self.manager = manager

    def create(self, name, description):
        name = re.sub(r"[^a-z0-9_]","_",name.lower().strip())
        logger.info(f"[dynamic_agent] creating '{name}': {description}")
        logic = _generate_agent_code(name, description, self.router)
        code = AGENT_TEMPLATE.format(logic=logic)
        logger.warning(f"[dynamic_agent] generated code:\n{code}")
        ok, err = _syntax_check(code)
        if not ok:
            logger.warning(f"[dynamic_agent] syntax error: {err}")
            logger.warning(f"[dynamic_agent] syntax check failed for '{name}', using fallback")
            logic = "    return \"fallback: \" + prompt"
            code = AGENT_TEMPLATE.format(logic=logic)
            ok, err = _syntax_check(code)
            if not ok:
                return f"❌ Could not generate valid code: {err}"
        path = _save_agent(name, code)
        try:
            mod = _load_module(name, path)
            self.manager.register_agent(name, mod.run)
            logger.info(f"[dynamic_agent] registered '{name}'")
            return (
                f"✅ Agent '{name}' created and registered!\n"
                f"Description: {description}\n"
                f"Use it: /goal {name}: <your request>"
            )
        except Exception as e:
            return f"❌ Saved but registration failed: {e}"

def load_dynamic_agents(manager):
    if not os.path.isdir(DYNAMIC_AGENTS_DIR):
        return 0
    count = 0
    for fname in os.listdir(DYNAMIC_AGENTS_DIR):
        if not fname.endswith("_agent.py"): continue
        name = fname.replace("_agent.py","")
        path = os.path.join(DYNAMIC_AGENTS_DIR, fname)
        try:
            mod = _load_module(name, path)
            manager.register_agent(name, mod.run)
            count += 1
        except Exception as e:
            logger.warning(f"[dynamic_agent] failed to load {fname}: {e}")
    return count
