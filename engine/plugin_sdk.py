"""
Plugin SDK — SHRRI Phase 14
Base class and decorators for writing SHRRI plugins.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass
class PluginMeta:
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = "unknown"
    requires: list = field(default_factory=list)  # other plugin names


class BasePlugin(ABC):
    """All plugins inherit from this."""
    meta: PluginMeta = None

    def on_load(self):
        """Called when plugin is loaded."""
        pass

    def on_unload(self):
        """Called when plugin is unloaded."""
        pass

    @abstractmethod
    def run(self, input_text: str, context: dict = None) -> str:
        """Main entry point."""
        ...


# Decorator-style plugin registration
_registered: dict[str, Callable] = {}


def plugin(name: str, version: str = "1.0.0", description: str = ""):
    """Decorator to register a function as a plugin."""
    def decorator(fn: Callable) -> Callable:
        fn._plugin_meta = PluginMeta(name=name, version=version, description=description)
        _registered[name] = fn
        return fn
    return decorator


def get_registered() -> dict:
    return {
        name: {
            "name": name,
            "version": fn._plugin_meta.version,
            "description": fn._plugin_meta.description,
            "type": "function"
        }
        for name, fn in _registered.items()
    }
