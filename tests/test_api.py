import unittest
import urllib.request
import json


class TestAPI(unittest.TestCase):
    BASE_URL = "http://localhost:8000"

    def test_root(self):
        url = f"{self.BASE_URL}/"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode())
        self.assertEqual(response.getcode(), 200)
        self.assertEqual(data, {"message": "Welcome to Guardrail AI"})

    def test_health(self):
        url = f"{self.BASE_URL}/health"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode())
        self.assertEqual(response.getcode(), 200)
        self.assertEqual(data, {"status": "healthy"})

    def test_policies(self):
        url = f"{self.BASE_URL}/policies"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode())
        self.assertEqual(response.getcode(), 200)
        self.assertIn("rules", data)

    def test_evaluate_allow(self):
        url = f"{self.BASE_URL}/evaluate"
        payload = {"tool": "database", "action": "delete", "record_count": 5}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode())
        self.assertEqual(response.getcode(), 200)
        self.assertEqual(data["decision"], "allow")

    def test_evaluate_block(self):
        url = f"{self.BASE_URL}/evaluate"
        payload = {"tool": "database", "action": "delete", "record_count": 500}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode())
        self.assertEqual(response.getcode(), 200)
        self.assertEqual(data["decision"], "block")
        self.assertEqual(data["matched_rule"], "block_large_delete")

    def test_execute_allow(self):
        url = f"{self.BASE_URL}/execute"
        payload = {"tool": "database", "action": "delete", "record_count": 5}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode())
        self.assertEqual(response.getcode(), 200)
        self.assertEqual(data["status"], "executed")
        self.assertEqual(data["decision"], "allow")
        self.assertEqual(data["tool_output"]["status"], "success")

    def test_execute_block(self):
        url = f"{self.BASE_URL}/execute"
        payload = {"tool": "database", "action": "delete", "record_count": 500}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode())
        self.assertEqual(response.getcode(), 200)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["decision"], "block")

    def test_simulate(self):
        url = f"{self.BASE_URL}/simulate"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode())
        self.assertEqual(response.getcode(), 200)
        self.assertEqual(data["simulation"], "completed")
        self.assertIn("results", data)
