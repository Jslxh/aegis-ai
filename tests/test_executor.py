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

    def test_executor_unknown_tool(self):
        result = ToolExecutor().execute({"tool": "nope", "action": "x"})
        self.assertEqual(result["status"], "error")
        self.assertIn("Unknown tool", result["message"])

    def test_executor_unsupported_action(self):
        result = ToolExecutor().execute({"tool": "database", "action": "drop"})
        self.assertEqual(result["status"], "error")
        self.assertIn("does not support action", result["message"])

    def test_list_tools_returns_plugins(self):
        tools = ToolExecutor().list_tools()
        self.assertGreaterEqual(len(tools), 3)
        names = {t["name"] for t in tools}
        self.assertIn("database", names)

    def test_simulate_database(self):
        result = ToolExecutor().simulate({"tool": "database", "action": "delete", "record_count": 10})
        self.assertTrue(result["tool_valid"])
        self.assertEqual(result["simulated_output"]["operation"], "delete 10 records")

    def test_simulate_unknown_tool(self):
        result = ToolExecutor().simulate({"tool": "nope", "action": "x"})
        self.assertFalse(result["tool_valid"])

    def test_simulate_unsupported_action(self):
        result = ToolExecutor().simulate({"tool": "database", "action": "drop"})
        self.assertFalse(result["tool_valid"])

    def test_email_tool_execute_and_simulate(self):
        executor = ToolExecutor()
        sent = executor.execute({"tool": "email", "action": "send", "recipient": "a@b.c"})
        self.assertEqual(sent["status"], "success")
        self.assertIn("a@b.c", sent["message"])
        sim = executor.simulate({"tool": "email", "action": "send", "recipient": "a@b.c"})
        self.assertEqual(sim["simulated_output"]["operation"], "send email to a@b.c")
        self.assertEqual(
            executor.execute({"tool": "email", "action": "bounce"})["status"], "error"
        )
        self.assertEqual(
            executor.simulate({"tool": "email", "action": "bounce"})["tool_valid"], False
        )

    def test_file_tool_execute_and_simulate(self):
        executor = ToolExecutor()
        read = executor.execute({"tool": "file", "action": "read", "path": "docs/x.txt"})
        self.assertEqual(read["status"], "success")
        self.assertIn("docs/x.txt", read["message"])
        sim = executor.simulate({"tool": "file", "action": "read", "path": "docs/x.txt"})
        self.assertEqual(sim["simulated_output"]["operation"], "read file at docs/x.txt")
        self.assertEqual(
            executor.execute({"tool": "file", "action": "write"})["status"], "error"
        )
        self.assertEqual(
            executor.simulate({"tool": "file", "action": "write"})["tool_valid"], False
        )

    def test_database_tool_simulate_default_count(self):
        sim = ToolExecutor().simulate({"tool": "database", "action": "delete"})
        self.assertEqual(sim["simulated_output"]["operation"], "delete 0 records")
