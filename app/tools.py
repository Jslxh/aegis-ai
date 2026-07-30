class DatabaseTool:

    def delete(self, record_count):

        return {
            "status": "success",
            "message": f"{record_count} records deleted"
        }


class EmailTool:

    def send(self, recipient):

        return {
            "status": "success",
            "message": f"Email sent to {recipient}"
        }


class FileTool:

    def read(self, path):

        return {
            "status": "success",
            "message": f"Read file {path}"
        }