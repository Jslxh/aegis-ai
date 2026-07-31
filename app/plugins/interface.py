from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseToolPlugin(ABC):
    """Plugin interface every tool plugin must implement.

    A plugin maps a tool name (e.g. ``database``) to a set of actions.
    New tools can be added by implementing this interface and dropping the
    module into a discovered directory; no core code changes are required.
    """

    name: str = ""
    description: str = ""
    version: str = "1.0.0"

    actions: Dict[str, Dict[str, Any]] = {}

    @abstractmethod
    def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the given action with the provided parameters."""
        raise NotImplementedError

    @abstractmethod
    def simulate(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return simulated output for the action without performing side effects."""
        raise NotImplementedError

    def info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "actions": self.actions,
        }
