class EmailTool:
    """Tool for sending emails."""

    def send(self, recipient: str) -> dict:
        return {
            "status": "success",
            "message": f"Email sent to {recipient}"
        }
