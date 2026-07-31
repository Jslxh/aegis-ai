import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.plugins.interface import BaseToolPlugin
from app.plugins.validator import validate_plugin


def _default_plugin_dirs() -> List[str]:
    """Default plugin search directories, plus any from GUARDRAIL_PLUGIN_DIRS."""
    root = Path(__file__).resolve().parent.parent.parent
    dirs = [str(root / "app" / "tools"), str(root / "plugins")]
    extra = os.getenv("GUARDRAIL_PLUGIN_DIRS")
    if extra:
        dirs.extend(d.strip() for d in extra.split(",") if d.strip())
    return dirs


class ToolRegistry:
    """Central registry of available tool plugins."""

    _default: Optional["ToolRegistry"] = None

    def __init__(self) -> None:
        self._plugins: Dict[str, BaseToolPlugin] = {}
        self._discovered: bool = False
        self._errors: List[str] = []

    @classmethod
    def get_default(cls) -> "ToolRegistry":
        if cls._default is None:
            cls._default = cls()
        return cls._default

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, plugin_cls: Any) -> List[str]:
        """Validate and register a plugin class. Returns validation errors."""
        errors = validate_plugin(plugin_cls)
        if errors:
            self._errors.extend(errors)
            return errors
        instance = plugin_cls()
        self._plugins[instance.name] = instance
        return []

    def register_instance(self, plugin: BaseToolPlugin) -> List[str]:
        errors = validate_plugin(type(plugin))
        if errors:
            self._errors.extend(errors)
            return errors
        self._plugins[plugin.name] = plugin
        return []

    def unregister(self, name: str) -> bool:
        if name in self._plugins:
            del self._plugins[name]
            return True
        return False

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[BaseToolPlugin]:
        return self._plugins.get(name)

    def has(self, name: str) -> bool:
        return name in self._plugins

    def names(self) -> List[str]:
        return list(self._plugins.keys())

    def list(self) -> List[BaseToolPlugin]:
        return list(self._plugins.values())

    def info(self) -> List[Dict[str, Any]]:
        return [p.info() for p in self._plugins.values()]

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    @property
    def is_discovered(self) -> bool:
        return self._discovered

    @property
    def errors(self) -> List[str]:
        return list(self._errors)

    def add_error(self, message: str) -> None:
        """Record a discovery/registration error (surfaces in /tools/info)."""
        self._errors.append(message)

    def discover(self) -> List[str]:
        """Dynamically discover plugins from the configured directories."""
        if self._discovered:
            return self.names()
        from app.plugins.discovery import discover_plugins

        discover_plugins(_default_plugin_dirs(), self)
        self._discovered = True
        return self.names()

    def reset(self) -> None:
        """Clear all plugins and discovery state (used in tests)."""
        self._plugins.clear()
        self._discovered = False
        self._errors.clear()
