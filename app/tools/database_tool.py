import os
import sqlite3
from app.plugins.interface import BaseToolPlugin


class DatabaseTool(BaseToolPlugin):
    """Tool for executing database operations."""

    name = "database"
    description = "Tool for executing database operations"
    version = "1.0.0"

    actions = {
        "delete": {
            "description": "Delete records from the database",
            "parameters": {
                "record_count": {
                    "type": "integer",
                    "required": True,
                    "description": "Number of records to delete",
                },
            },
        },
    }

    def _get_db_path(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        db_dir = os.path.join(project_root, "data")
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, "dummy.db")

    def init_database(self):
        db_path = self._get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dummy_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Check if table already has rows
        cursor.execute("SELECT COUNT(*) FROM dummy_records;")
        count = cursor.fetchone()[0]
        
        if count < 10000:
            rows_to_insert = 10000 - count
            # Insert in chunks to avoid blocking
            batch_size = 2000
            for i in range(0, rows_to_insert, batch_size):
                chunk = min(batch_size, rows_to_insert - i)
                cursor.executemany(
                    "INSERT INTO dummy_records (data) VALUES (?);",
                    [(f"dummy record {x}",) for x in range(chunk)]
                )
            conn.commit()
            
        conn.close()

    def execute(self, action, params):
        if action == "delete":
            return self._delete(params.get("record_count"))
        return {"status": "error", "message": f"Unsupported action: {action}"}

    def _delete(self, record_count):
        self.init_database()
        
        db_path = self._get_db_path()
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Find record IDs to delete
            cursor.execute("SELECT id FROM dummy_records LIMIT ?;", (record_count,))
            ids = [row[0] for row in cursor.fetchall()]
            
            if not ids:
                conn.close()
                return {
                    "status": "success",
                    "message": "0 records deleted from dummy.db (database empty)",
                    "deleted_count": 0,
                    "remaining_records": 0
                }
                
            cursor.execute(
                f"DELETE FROM dummy_records WHERE id IN ({','.join('?' for _ in ids)});",
                ids
            )
            deleted_count = cursor.rowcount
            conn.commit()
            
            cursor.execute("SELECT COUNT(*) FROM dummy_records;")
            remaining_count = cursor.fetchone()[0]
            conn.close()
            
            return {
                "status": "success",
                "message": f"{deleted_count} records deleted from dummy.db (remaining: {remaining_count})",
                "deleted_count": deleted_count,
                "remaining_records": remaining_count
            }
        except Exception as e:
            return {"status": "error", "message": f"Database operation failed: {str(e)}"}

    def simulate(self, action, params):
        if action == "delete":
            count = params.get("record_count", 0)
            return {
                "status": "success",
                "operation": f"delete {count} records",
                "target": "database",
                "side_effects": ["Data will be permanently deleted"],
            }
        return {"status": "error", "message": f"Unsupported action: {action}"}
