"""
Auto Discovery — SHRRI Phase 14
Scans plugins/ dir and auto-registers any valid plugin files.
"""
from pathlib import Path
from engine.plugin_registry import PluginRegistry

PLUGINS_DIR = Path.home() / "shrri" / "plugins"


def discover_and_register() -> dict:
    registry = PluginRegistry()
    results = {}
    if not PLUGINS_DIR.exists():
        return results
    for py_file in PLUGINS_DIR.glob("*.py"):
        name = py_file.stem
        if name.startswith("_"):
            continue
        if name not in [p["name"] for p in registry.list_all()]:
            registry.register(name, str(py_file), {"source": "auto_discovery"})
            results[name] = "registered"
        else:
            results[name] = "already_registered"
    return results


def list_available() -> list:
    """List all .py files in plugins dir."""
    if not PLUGINS_DIR.exists():
        return []
    return [f.stem for f in PLUGINS_DIR.glob("*.py") if not f.name.startswith("_")]
