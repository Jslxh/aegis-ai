import unittest
from app.core.executor import ToolExecutor


class TestExecutor(unittest.TestCase):

    def test_executor_database_delete(self):
        executor = ToolExecutor()
        request = {"tool": "database", "action": "delete", "record_count": 10}
        result = executor.execute(request)
        self.assertEqual(result["status"], "success")
        self.assertIn("10 records deleted", result["message"])

    def test_executor_dry_run(self):
        executor = ToolExecutor()
        request = {"tool": "database", "action": "delete", "record_count": 10}
        result = executor.execute(request, dry_run=True)
        self.assertEqual(result["status"], "DRY_RUN")
        self.assertTrue(result["simulated"])
