"""
Plugin Registry — SHRRI Phase 14
Stores, loads, and manages installed plugins.
"""
import json, os, importlib.util, sys
from pathlib import Path
from datetime import datetime

REGISTRY_PATH = Path.home() / ".shrri" / "plugin_registry.json"
PLUGINS_DIR = Path.home() / "shrri" / "plugins"


class PluginRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._registry = self._load()
        self._loaded: dict = {}
        self._initialized = True

    def _load(self) -> dict:
        if REGISTRY_PATH.exists():
            with open(REGISTRY_PATH) as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(REGISTRY_PATH, "w") as f:
            json.dump(self._registry, f, indent=2)

    def register(self, name: str, path: str, meta: dict = None):
        self._registry[name] = {
            "name": name,
            "path": str(path),
            "meta": meta or {},
            "enabled": True,
            "installed_at": datetime.now().isoformat()
        }
        self._save()

    def unregister(self, name: str):
        self._registry.pop(name, None)
        self._loaded.pop(name, None)
        self._save()

    def enable(self, name: str):
        if name in self._registry:
            self._registry[name]["enabled"] = True
            self._save()

    def disable(self, name: str):
        if name in self._registry:
            self._registry[name]["enabled"] = False
            self._loaded.pop(name, None)
            self._save()

    def load(self, name: str) -> object:
        if name in self._loaded:
            return self._loaded[name]
        entry = self._registry.get(name)
        if not entry or not entry["enabled"]:
            return None
        path = entry["path"]
        if not os.path.exists(path):
            return None
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        self._loaded[name] = mod
        return mod

    def load_all(self) -> dict:
        results = {}
        for name, entry in self._registry.items():
            if entry["enabled"]:
                mod = self.load(name)
                results[name] = "loaded" if mod else "failed"
        return results

    def list_all(self) -> list:
        return [
            {
                "name": k,
                "enabled": v["enabled"],
                "installed": v["installed_at"][:10],
                "meta": v.get("meta", {})
            }
            for k, v in self._registry.items()
        ]

    def run(self, name: str, input_text: str, context: dict = None) -> str:
        mod = self.load(name)
        if not mod:
            return f"Plugin '{name}' not found or disabled"
        if hasattr(mod, "run"):
            return mod.run(input_text, context or {})
        return f"Plugin '{name}' has no run() function"
