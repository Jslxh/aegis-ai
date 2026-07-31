from app.plugins.interface import BaseToolPlugin


class LogTool(BaseToolPlugin):
    """Example plugin demonstrating dynamic discovery.

    Drop a module like this into the plugins/ directory (or any directory
    listed in GUARDRAIL_PLUGIN_DIRS) and it is discovered automatically.
    No changes to ToolExecutor are required.
    """

    name = "log"
    description = "Write a log entry"
    version = "1.0.0"

    actions = {
        "write": {
            "description": "Write a log entry",
            "parameters": {
                "level": {
                    "type": "string",
                    "required": True,
                    "description": "Log level (info, warning, error)",
                },
                "message": {
                    "type": "string",
                    "required": True,
                    "description": "Log message",
                },
            },
        },
    }

    def execute(self, action, params):
        if action == "write":
            level = params.get("level", "info")
            message = params.get("message", "")
            return {
                "status": "success",
                "message": f"[{level}] {message}",
            }
        return {"status": "error", "message": f"Unsupported action: {action}"}

    def simulate(self, action, params):
        if action == "write":
            return {
                "status": "success",
                "operation": f"write log entry at level {params.get('level', 'info')}",
                "target": "log sink",
                "side_effects": ["A log entry will be written"],
            }
        return {"status": "error", "message": f"Unsupported action: {action}"}
