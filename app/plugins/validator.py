import inspect
import re
from typing import Any, List

from app.plugins.interface import BaseToolPlugin

NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class PluginValidationError(Exception):
    """Raised when a plugin fails validation."""


def validate_plugin(plugin_cls: Any) -> List[str]:
    """Validate a plugin class. Returns a list of error messages (empty if valid)."""
    errors: List[str] = []

    if not inspect.isclass(plugin_cls):
        return ["Plugin must be a class"]

    if plugin_cls is BaseToolPlugin:
        return ["BaseToolPlugin itself is not a registrable plugin"]

    if not issubclass(plugin_cls, BaseToolPlugin):
        return ["Plugin must subclass BaseToolPlugin"]

    if inspect.isabstract(plugin_cls):
        return ["Plugin must implement all abstract methods (execute, simulate)"]

    name = getattr(plugin_cls, "name", None)
    if not name or not isinstance(name, str):
        errors.append("Plugin 'name' is required and must be a non-empty string")
    elif not NAME_PATTERN.match(name):
        errors.append(
            f"Invalid plugin name '{name}'. Must match {NAME_PATTERN.pattern}"
        )

    description = getattr(plugin_cls, "description", None)
    if not description or not isinstance(description, str):
        errors.append(
            "Plugin 'description' is required and must be a non-empty string"
        )

    actions = getattr(plugin_cls, "actions", None)
    if not actions or not isinstance(actions, dict):
        errors.append("Plugin must declare a non-empty 'actions' dict")
    else:
        for action_name, schema in actions.items():
            if not isinstance(schema, dict):
                errors.append(f"Action '{action_name}' schema must be a dict")
                continue
            params = schema.get("parameters")
            if params is None:
                continue
            if not isinstance(params, dict):
                errors.append(f"Action '{action_name}' parameters must be a dict")
                continue
            for param_name, param_schema in params.items():
                if not isinstance(param_schema, dict) or "type" not in param_schema:
                    errors.append(
                        f"Parameter '{param_name}' of action '{action_name}' "
                        "must be a dict with a 'type'"
                    )

    for method in ("execute", "simulate"):
        if method not in plugin_cls.__dict__:
            errors.append(f"Plugin must implement '{method}(action, params)'")

    return errors


def ensure_valid_plugin(plugin_cls: Any) -> None:
    """Validate a plugin class and raise PluginValidationError if invalid."""
    errors = validate_plugin(plugin_cls)
    if errors:
        raise PluginValidationError("; ".join(errors))
