import pytest
from app.api import ai_routes

@pytest.mark.api
def test_chat_conversational(client, auth_headers_factory, mock_groq):
    res = client.post(
        "/ai/chat",
        json={"message": "hello"},
        headers=auth_headers_factory("viewer")
    )
    assert res.status_code == 200
    assert res.json()["is_tool_call"] is False
    assert "response" in res.json()

@pytest.mark.api
def test_chat_tool_call_blocked(client, auth_headers_factory, monkeypatch):
    from app.api import ai_routes
    
    # Mock chat to return a tool call that triggers a policy block
    class FakeGroq:
        def run_chat_agent(self, *a, **k):
            return {
                "success": True,
                "is_tool_call": True,
                "response": "Deleting database records...",
                "tool_call": {
                    "tool": "database",
                    "action": "delete",
                    "record_count": 500
                }
            }
        explain_decision = lambda self, *a, **k: {
            "success": True,
            "explanation": "Blocked by policy rule",
            "recommendations": ["Do not delete so many records"],
            "risk_level": "high",
            "summary": "Block description"
        }
        
    monkeypatch.setattr(ai_routes, "groq", FakeGroq())
    
    res = client.post(
        "/ai/chat",
        json={"message": "delete 500 records from database"},
        headers=auth_headers_factory("operator")
    )
    assert res.status_code == 200
    body = res.json()
    assert body["is_tool_call"] is True
    assert body["execution_result"]["decision"] == "block"
    assert body["explanation"] == "Blocked by policy rule"

@pytest.mark.api
def test_email_domain_intercept(client, auth_headers_factory):
    # Test internal email allowed
    res = client.post(
        "/execute",
        json={"tool": "email", "action": "send", "recipient": "bob@company.com"},
        headers=auth_headers_factory("operator")
    )
    assert res.status_code == 200
    assert res.json()["status"] == "executed"

    # Test external email requires human approval (suspended)
    res = client.post(
        "/execute",
        json={"tool": "email", "action": "send", "recipient": "mithrajith46@gmail.com"},
        headers=auth_headers_factory("operator")
    )
    assert res.status_code == 200
    assert res.json()["status"] == "waiting_for_human"
