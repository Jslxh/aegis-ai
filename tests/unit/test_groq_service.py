"""Unit tests for the Groq service (mocked client) and prompt builders."""

import json

import pytest

from app.services.groq_service import GroqService, _extract_json
from app.services import prompts


class FakeResponse:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})})()]


class FakeClient:
    def __init__(self, content):
        self._content = content
        self.calls = []

    @property
    def chat(self):
        return self

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse(self._content)


@pytest.mark.unit
class TestExtractJson:
    def test_direct_json(self):
        assert _extract_json('{"a": 1}') == {"a": 1}

    def test_embedded_json(self):
        assert _extract_json('prefix text {"a": 1} suffix') == {"a": 1}

    def test_fenced_json(self):
        result = _extract_json('```json\n{"a": 1}\n```')
        assert result == {"a": 1}

    def test_garbage_returns_none(self):
        assert _extract_json("not json at all") is None
        assert _extract_json("") is None
        assert _extract_json(None) is None


@pytest.mark.unit
class TestGroqService:
    def test_init_requires_api_key(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            GroqService(api_key=None)

    def test_chat_success(self):
        svc = GroqService(api_key="test-key")
        fake = FakeClient('{"explanation": "ok"}')
        svc.client = fake
        result = svc.chat([{"role": "user", "content": "hi"}])
        assert result["success"] is True
        assert result["content"] == '{"explanation": "ok"}'
        assert result["model"] == svc.model
        assert fake.calls[0]["model"] == svc.model

    def test_chat_failure_captures_error(self):
        svc = GroqService(api_key="test-key")

        class ExplodingClient:
            @property
            def chat(self):
                return self

            @property
            def completions(self):
                return self

            def create(self, **kwargs):
                raise RuntimeError("API down")

        svc.client = ExplodingClient()
        result = svc.chat([])
        assert result["success"] is False
        assert "API down" in result["error"]

    def test_structured_parses_fields(self):
        svc = GroqService(api_key="test-key")
        svc.client = FakeClient(
            json.dumps(
                {
                    "explanation": "why",
                    "risk_analysis": "risky",
                    "risk_level": "high",
                    "recommendations": ["a", "b"],
                    "confidence": 0.85,
                    "summary": "sum",
                }
            )
        )
        result = svc.explain_decision("r1", "block", "reason", {"tool": "db"})
        assert result["success"] is True
        assert result["explanation"] == "why"
        assert result["risk_level"] == "high"
        assert result["recommendations"] == ["a", "b"]
        assert result["confidence"] == 0.85

    def test_structured_falls_back_to_raw_text(self):
        svc = GroqService(api_key="test-key")
        svc.client = FakeClient('{"foo": "bar"}')
        result = svc.explain_decision(None, "allow", "reason", {})
        assert result["explanation"] == '{"foo": "bar"}'

    def test_structured_string_recommendation_normalized(self):
        svc = GroqService(api_key="test-key")
        svc.client = FakeClient('{"explanation": "x", "recommendations": "single"}')
        result = svc.analyze_risk("db", "delete", {}, "block")
        assert result["recommendations"] == ["single"]

    def test_structured_failure_passthrough(self):
        svc = GroqService(api_key="test-key")
        result = svc._structured({"success": False, "error": "boom"})
        assert result["success"] is False
        assert "explanation" not in result

    def test_all_entrypoints_build_and_call(self):
        svc = GroqService(api_key="test-key")
        svc.client = FakeClient('{"explanation": "x", "recommendations": ["r"]}')
        assert svc.hitl_summary({"tool": "db"}, "require_hitl", "reason")["success"] is True
        assert svc.audit_summary({"tool": "db", "decision": "block"})["success"] is True
        assert svc.simulation_analysis({"blocked": 1}, [])["success"] is True


@pytest.mark.unit
class TestPromptBuilders:
    def test_builders_return_system_and_user_messages(self):
        messages = prompts.build_decision_explanation_prompt("r1", "block", "no", {"tool": "db"})
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert prompts.GLOBAL_CONSTRAINT in messages[0]["content"]

    def test_risk_analysis_prompt_includes_decision(self):
        messages = prompts.build_risk_analysis_prompt("db", "delete", {"n": 1}, "block")
        assert "block" in messages[1]["content"]

    def test_hitl_prompt(self):
        messages = prompts.build_hitl_summary_prompt({"tool": "email"}, "require_hitl", "why")
        assert "require_hitl" in messages[1]["content"]

    def test_audit_prompt(self):
        messages = prompts.build_audit_summary_prompt({"tool": "db", "decision": "block"})
        assert "block" in messages[1]["content"]

    def test_simulation_prompt(self):
        messages = prompts.build_simulation_analysis_prompt(
            {"blocked": 1}, [{"scenario": "Large Delete", "decision": "block"}]
        )
        assert "Large Delete" in messages[1]["content"]
