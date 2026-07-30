from app.tools import DatabaseTool, EmailTool, FileTool


class ToolExecutor:

    def __init__(self):
        self.db = DatabaseTool()
        self.email = EmailTool()
        self.file = FileTool()

    def execute(self, request, dry_run=False):

        if dry_run:
            return {
                "status": "DRY_RUN",
                "message": "Execution skipped. Policy evaluation completed successfully.",
                "simulated": True
            }

        tool = request["tool"]

        if tool == "database":
            return self.db.delete(request["record_count"])

        elif tool == "email":
            return self.email.send(request["recipient"])

        elif tool == "file":
            return self.file.read(request["path"])

        # Unknown tool
        return {
            "status": "error",
            "message": f"Unknown tool: {tool}"
        }