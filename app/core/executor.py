from typing import Any, Dict, Optional

from app.plugins.interface import BaseToolPlugin
from app.plugins.registry import ToolRegistry


class ToolExecutor:
    """Executes tool actions via the plugin registry.

    New tools are added by implementing BaseToolPlugin and placing the module
    in a discovered directory (or registering it explicitly). This class is
    intentionally never modified when a new tool is added (Open/Closed).
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or ToolRegistry.get_default()
        if not self.registry.is_discovered:
            self.registry.discover()

    def list_tools(self) -> list[Dict[str, Any]]:
        """Return metadata for every registered tool plugin."""
        return self.registry.info()

    @staticmethod
    def _resolve(request: Dict[str, Any]) -> tuple[str, str, Dict[str, Any]]:
        tool = request.get("tool", "")
        action = request.get("action", "")
        params = {
            k: v for k, v in request.items()
            if k not in ("tool", "action", "dry_run")
        }
        return tool, action, params

    def execute(self, request: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        if dry_run:
            return {
                "status": "DRY_RUN",
                "message": "Execution skipped. Policy evaluation completed successfully.",
                "simulated": True,
            }

        tool, action, params = self._resolve(request)
        plugin: Optional[BaseToolPlugin] = self.registry.get(tool)

        if plugin is None:
            return {"status": "error", "message": f"Unknown tool: {tool}"}

        if action not in plugin.actions:
            return {
                "status": "error",
                "message": f"Tool '{tool}' does not support action '{action}'",
            }

        return plugin.execute(action, params)

    def simulate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        tool, action, params = self._resolve(request)
        plugin: Optional[BaseToolPlugin] = self.registry.get(tool)

        if plugin is None:
            return {
                "tool_valid": False,
                "simulated_output": {
                    "status": "error",
                    "message": f"Unknown tool: {tool}",
                },
            }

        if action not in plugin.actions:
            return {
                "tool_valid": False,
                "simulated_output": {
                    "status": "error",
                    "message": f"Tool '{tool}' does not support action '{action}'",
                },
            }

        simulated = plugin.simulate(action, params)
        return {"tool_valid": True, "simulated_output": simulated}
