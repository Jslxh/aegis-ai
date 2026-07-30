from typing import Dict, Any
from app.tools.database_tool import DatabaseTool
from app.tools.email_tool import EmailTool
from app.tools.file_tool import FileTool


class ToolExecutor:
    """Executes validated tool actions."""

    def __init__(self):
        self.db = DatabaseTool()
        self.email = EmailTool()
        self.file = FileTool()

    def execute(self, request: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        if dry_run:
            return {
                "status": "DRY_RUN",
                "message": "Execution skipped. Policy evaluation completed successfully.",
                "simulated": True
            }

        tool = request.get("tool")

        if tool == "database":
            return self.db.delete(request.get("record_count"))
        elif tool == "email":
            return self.email.send(request.get("recipient"))
        elif tool == "file":
            return self.file.read(request.get("path"))

        return {
            "status": "error",
            "message": f"Unknown tool: {tool}"
        }
