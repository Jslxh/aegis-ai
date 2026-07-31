from app.plugins.interface import BaseToolPlugin


class FileTool(BaseToolPlugin):
    """Tool for reading local files."""

    name = "file"
    description = "Tool for reading local files"
    version = "1.0.0"

    actions = {
        "read": {
            "description": "Read a file from the filesystem",
            "parameters": {
                "path": {
                    "type": "string",
                    "required": True,
                    "description": "Path to the file",
                },
            },
        },
    }

    def execute(self, action, params):
        if action == "read":
            return self._read(params.get("path"))
        return {"status": "error", "message": f"Unsupported action: {action}"}

    def _read(self, path):
        return {"status": "success", "message": f"Read file {path}"}

    def simulate(self, action, params):
        if action == "read":
            path = params.get("path", "unknown")
            return {
                "status": "success",
                "operation": f"read file at {path}",
                "target": "filesystem",
                "side_effects": ["Filesystem will be accessed"],
            }
        return {"status": "error", "message": f"Unsupported action: {action}"}
