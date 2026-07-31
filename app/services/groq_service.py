import json
import os
import re
import time
import logging
from typing import Any, Dict, Optional

from groq import Groq
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


def _extract_json(content: str) -> Optional[Dict[str, Any]]:
    """Best-effort extraction of a JSON object from an LLM response."""
    if not content:
        return None

    # Try direct parse first
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # Try extracting the first {...} block
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

    # Try fenced code block
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

    return None


class GroqService:
    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: int = 30):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not set. Provide api_key or set GROQ_API_KEY in .env")
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.timeout = timeout
        self.client = Groq(api_key=self.api_key)

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.3, max_tokens: int = 1024) -> dict[str, Any]:
        start = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout,
            )
            latency = round(time.time() - start, 3)
            content = response.choices[0].message.content if response.choices else ""
            result = {"success": True, "content": content, "model": self.model, "latency": latency}
            logger.info("Groq API success | model=%s | latency=%ss", self.model, latency)
            return result
        except Exception as e:
            latency = round(time.time() - start, 3)
            logger.error("Groq API error | model=%s | latency=%ss | error=%s", self.model, latency, str(e))
            return {
                "success": False,
                "content": None,
                "model": self.model,
                "latency": latency,
                "error": str(e),
            }

    def _structured(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Augment a chat() result with parsed structured fields.
        The LLM is advisory only: policy decisions are never derived from AI output."""
        if not result.get("success"):
            return result

        content = result.get("content") or ""
        data = _extract_json(content)

        explanation = (data or {}).get("explanation")
        risk_analysis = (data or {}).get("risk_analysis")
        risk_level = (data or {}).get("risk_level")
        recommendations = (data or {}).get("recommendations")
        confidence = (data or {}).get("confidence")
        summary = (data or {}).get("summary")

        # Fall back to raw text if structured extraction failed
        if not explanation and content:
            explanation = content

        if isinstance(recommendations, str):
            recommendations = [recommendations]

        result["explanation"] = explanation
        result["risk_analysis"] = risk_analysis
        result["risk_level"] = risk_level
        result["recommendations"] = recommendations if isinstance(recommendations, list) else None
        result["confidence"] = float(confidence) if isinstance(confidence, (int, float)) else None
        result["summary"] = summary
        return result

    def explain_decision(self, matched_rule: str | None, decision: str, reason: str, request: dict) -> dict[str, Any]:
        from app.services.prompts import build_decision_explanation_prompt
        messages = build_decision_explanation_prompt(matched_rule, decision, reason, request)
        return self._structured(self.chat(messages))

    def analyze_risk(self, tool: str, action: str, parameters: dict, decision: str) -> dict[str, Any]:
        from app.services.prompts import build_risk_analysis_prompt
        messages = build_risk_analysis_prompt(tool, action, parameters, decision)
        return self._structured(self.chat(messages))

    def hitl_summary(self, request: dict, decision: str, reason: str) -> dict[str, Any]:
        from app.services.prompts import build_hitl_summary_prompt
        messages = build_hitl_summary_prompt(request, decision, reason)
        return self._structured(self.chat(messages))

    def audit_summary(self, record: dict) -> dict[str, Any]:
        from app.services.prompts import build_audit_summary_prompt
        messages = build_audit_summary_prompt(record)
        return self._structured(self.chat(messages))

    def simulation_analysis(self, summary: dict, results: list) -> dict[str, Any]:
        from app.services.prompts import build_simulation_analysis_prompt
        messages = build_simulation_analysis_prompt(summary, results)
        return self._structured(self.chat(messages))

    def run_chat_agent(self, message: str, history: Optional[list[dict[str, str]]] = None) -> dict[str, Any]:
        from app.services.prompts import build_chat_agent_prompt
        messages = build_chat_agent_prompt(message, history)
        result = self.chat(messages)
        if not result.get("success"):
            return result

        content = result.get("content") or ""
        parsed = _extract_json(content)
        if parsed:
            result.update(parsed)
        else:
            result["is_tool_call"] = False
            result["response"] = content
        return result
