import unittest
from app.core.guardrail import Guardrail


class TestGuardrail(unittest.TestCase):

    def test_guardrail_evaluate_allow(self):
        guardrail = Guardrail()
        request = {"tool": "database", "action": "delete", "record_count": 5}
        result = guardrail.evaluate(request)
        self.assertEqual(result["decision"], "allow")
        self.assertIsNone(result["matched_rule"])

    def test_guardrail_evaluate_block(self):
        guardrail = Guardrail()
        request = {"tool": "database", "action": "delete", "record_count": 500}
        result = guardrail.evaluate(request)
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["matched_rule"], "block_large_delete")
