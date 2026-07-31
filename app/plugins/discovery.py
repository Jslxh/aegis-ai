import importlib.util
import inspect
from pathlib import Path
from typing import Any, List, Optional

from app.plugins.interface import BaseToolPlugin
from app.plugins.registry import ToolRegistry


def _iter_plugin_files(directory: Path):
    """Yield python plugin files within a directory tree."""
    if not directory.is_dir():
        return
    for path in sorted(directory.iterdir()):
        if path.is_dir():
            if not path.name.startswith("_") and not path.name.startswith("."):
                yield from _iter_plugin_files(path)
        elif (
            path.suffix == ".py"
            and path.name != "__init__.py"
            and not path.name.startswith("_")
        ):
            yield path


def _load_module(path: Path) -> Optional[Any]:
    """Load a python module from a file path."""
    module_name = f"guardrail_plugin_{path.parent.name}_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discover_plugins(dirs, registry: ToolRegistry) -> List[str]:
    """Scan directories for BaseToolPlugin subclasses and register them."""
    registered: List[str] = []
    for directory in dirs:
        for file_path in _iter_plugin_files(Path(directory)):
            try:
                module = _load_module(file_path)
            except Exception as exc:
                registry.add_error(
                    f"Failed to load plugin module {file_path}: {exc}"
                )
                continue
            if module is None:
                continue
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj is BaseToolPlugin:
                    continue
                if issubclass(obj, BaseToolPlugin) and obj.__module__ == module.__name__:
                    if not registry.has(getattr(obj, "name", "")):
                        errors = registry.register(obj)
                        if not errors:
                            registered.append(obj.name)
    return registered


def register_tool(plugin_cls: Any):
    """Decorator: explicitly register a plugin with the default registry."""
    ToolRegistry.get_default().register(plugin_cls)
    return plugin_cls
