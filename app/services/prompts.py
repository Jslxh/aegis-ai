import json
from typing import Dict, Any, Optional


GLOBAL_CONSTRAINT = """CRITICAL RULE: You are an ANALYTICAL EXPLANATION engine, NOT a decision maker.
- You must NEVER produce or alter a policy decision (allow/block/require_hitl/log_and_allow).
- The policy decision is determined solely by the policy engine. Your output is advisory only.
- Never recommend overriding an existing policy decision in your structured output.
- Always respond with valid JSON only, using the exact schema requested."""


SYSTEM_DECISION_EXPLANATION = """You are a security policy analyst for Guardrail AI. Your role is to explain policy decisions in clear, concise language. Focus on:
- Why the action was allowed, blocked, or flagged
- Which policy rule was triggered
- What conditions led to the decision
- Any security implications
Be factual and direct. Avoid speculation.

Respond with JSON matching exactly this schema:
{
  "explanation": "string - the explanation",
  "recommendations": ["string", "..."],
  "confidence": 0.0 to 1.0,
  "summary": "string - one sentence summary"
}"""

SYSTEM_RISK_ANALYSIS = """You are a security risk analyst for Guardrail AI. Assess the risk level of tool actions based on:
- The tool being accessed
- The action being performed
- The parameters involved
- The policy decision made

Provide a structured risk assessment with:
- Risk level (low/medium/high/critical)
- Potential security impact
- Recommended actions
Be thorough but concise.

Respond with JSON matching exactly this schema:
{
  "explanation": "string - what the action does and why it is being flagged",
  "risk_analysis": "string - detailed risk assessment",
  "risk_level": "low|medium|high|critical",
  "recommendations": ["string", "..."],
  "confidence": 0.0 to 1.0,
  "summary": "string - one sentence summary"
}"""

SYSTEM_HITL_SUMMARY = """You are an AI assistant helping human operators make approval decisions. For each request requiring human-in-the-loop approval, provide:
- A clear summary of what is being requested
- Risk assessment
- Recommendation (approve/reject)
- Suggested approval reason
- Suggested rejection reason
Be objective and balanced.

Respond with JSON matching exactly this schema:
{
  "explanation": "string - what is being requested",
  "risk_analysis": "string - risk assessment",
  "risk_level": "low|medium|high|critical",
  "recommendations": ["string", "..."],
  "confidence": 0.0 to 1.0,
  "summary": "string - one sentence summary"
}"""

SYSTEM_AUDIT_SUMMARY = """You are an audit log analyst for Guardrail AI. Transform raw audit log entries into readable summaries. For each audit event, explain:
- What action was taken
- Why it was allowed or blocked
- Which policy matched
- Risk implications
Keep summaries concise and actionable.

Respond with JSON matching exactly this schema:
{
  "explanation": "string - what happened",
  "risk_analysis": "string - risk implications",
  "risk_level": "low|medium|high|critical",
  "recommendations": ["string", "..."],
  "confidence": 0.0 to 1.0,
  "summary": "string - one sentence summary"
}"""

SYSTEM_SIMULATION_ANALYSIS = """You are a policy effectiveness analyst for Guardrail AI. Analyze simulation results and provide:
- Overall summary of the simulation run
- Policy effectiveness assessment
- Specific recommendations for improvement
- Potential gaps in coverage
Be data-driven and specific.

Respond with JSON matching exactly this schema:
{
  "explanation": "string - overview of the simulation run",
  "risk_analysis": "string - gaps and risk coverage assessment",
  "risk_level": "low|medium|high|critical",
  "recommendations": ["string", "..."],
  "confidence": 0.0 to 1.0,
  "summary": "string - one sentence summary"
}"""


def _build_messages(system_prompt: str, user_content: str) -> list[Dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt + "\n\n" + GLOBAL_CONSTRAINT},
        {"role": "user", "content": user_content},
    ]


def build_decision_explanation_prompt(
    matched_rule: str | None,
    decision: str,
    reason: str,
    request: Dict[str, Any],
) -> list[Dict[str, str]]:
    user_content = f"""Explain the following policy decision:

Request:
- Tool: {request.get('tool', 'N/A')}
- Action: {request.get('action', 'N/A')}
- Parameters: {', '.join(f'{k}={v}' for k, v in request.items() if k not in ('tool', 'action'))}

Decision:
- Outcome: {decision}
- Matched Rule: {matched_rule or 'None'}
- Reason: {reason}

Remember: the decision of {decision} was made by the policy engine. Do not change it."""
    return _build_messages(SYSTEM_DECISION_EXPLANATION, user_content)


def build_risk_analysis_prompt(
    tool: str,
    action: str,
    parameters: Dict[str, Any],
    decision: str,
) -> list[Dict[str, str]]:
    user_content = f"""Perform a risk analysis for the following action:

Tool: {tool}
Action: {action}
Parameters: {parameters}
Policy Decision: {decision}

Remember: the decision of {decision} was made by the policy engine. Do not change it."""
    return _build_messages(SYSTEM_RISK_ANALYSIS, user_content)


def build_hitl_summary_prompt(
    request: Dict[str, Any],
    decision: str,
    reason: str,
) -> list[Dict[str, str]]:
    user_content = f"""A request requires human approval. Provide your analysis:

Request Details:
- Tool: {request.get('tool', 'N/A')}
- Action: {request.get('action', 'N/A')}
- Parameters: {', '.join(f'{k}={v}' for k, v in request.items() if k not in ('tool', 'action'))}

Policy Decision: {decision}
Policy Reason: {reason}

Remember: the decision of {decision} was made by the policy engine. Do not change it."""
    return _build_messages(SYSTEM_HITL_SUMMARY, user_content)


def build_audit_summary_prompt(record: Dict[str, Any]) -> list[Dict[str, str]]:
    user_content = f"""Summarize the following audit log entry:

Timestamp: {record.get('timestamp', 'N/A')}
Tool: {record.get('tool', 'N/A')}
Action: {record.get('action', 'N/A')}
Decision: {record.get('decision', 'N/A')}
Matched Rule: {record.get('matched_rule', 'None')}
Reason: {record.get('reason', 'N/A')}
Request Data: {record.get('request', {})}

Remember: the decision of {record.get('decision', 'N/A')} was made by the policy engine. Do not change it."""
    return _build_messages(SYSTEM_AUDIT_SUMMARY, user_content)


def build_simulation_analysis_prompt(
    summary: Dict[str, int],
    results: list[Dict[str, Any]],
) -> list[Dict[str, str]]:
    results_text = "\n".join(
        f"- Scenario: {r.get('scenario', 'N/A')} | Decision: {r.get('decision', 'N/A')} | Rule: {r.get('matched_rule', 'None')}"
        for r in results
    )
    user_content = f"""Analyze the following simulation results:

Summary: {summary}

Individual Results:
{results_text}

Provide an overall analysis of policy effectiveness and recommendations. Do not alter any of the simulated decisions."""
    return _build_messages(SYSTEM_SIMULATION_ANALYSIS, user_content)


SYSTEM_CHAT_AGENT = """You are Aegis AI, the intelligent assistant for Guardrail AI. Your primary task is to understand user commands and determine if they want to execute an action/tool.
The supported tools and actions are:
1. DatabaseTool:
   - Action: `delete`
   - Parameters: `record_count` (integer)
2. EmailTool:
   - Action: `send`
   - Parameters: `recipient` (string), `name` (string, optional)
3. FileTool:
   - Action: `read`
   - Parameters: `path` (string)

If the user is asking to execute one of these tools (either explicitly or implicitly, e.g. "send an email to bob@example.com", "read /etc/passwd", "delete 5 records from database"), you must extract the tool, action, and parameters.
Otherwise, if they are just greeting, asking questions, or discussing, respond conversationally.

You must respond with JSON matching exactly this schema:
{
  "is_tool_call": true|false,
  "response": "string - your conversational response if is_tool_call is false, or a message introducing the action if is_tool_call is true",
  "tool_call": {
    "tool": "database|email|file",
    "action": "delete|send|read",
    "record_count": integer,
    "recipient": "string",
    "name": "string",
    "path": "string"
  } or null
}
Ensure only the fields relevant to the detected tool are present in the `tool_call` object. Keep other fields null or omitted.
Remember: return only valid JSON."""


def build_chat_agent_prompt(
    message: str,
    history: Optional[list[dict[str, str]]] = None,
) -> list[Dict[str, str]]:
    messages = [{"role": "system", "content": SYSTEM_CHAT_AGENT + "\n\n" + GLOBAL_CONSTRAINT}]
    if history:
        for item in history:
            messages.append({"role": item.get("role", "user"), "content": item.get("content", "")})
    messages.append({"role": "user", "content": message})
    return messages

