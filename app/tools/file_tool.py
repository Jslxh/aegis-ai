class FileTool:
    """Tool for reading local files."""

    def read(self, path: str) -> dict:
        return {
            "status": "success",
            "message": f"Read file {path}"
        }
