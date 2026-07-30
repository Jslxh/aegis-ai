class DatabaseTool:
    """Tool for executing database operations."""

    def delete(self, record_count: int) -> dict:
        return {
            "status": "success",
            "message": f"{record_count} records deleted"
        }
