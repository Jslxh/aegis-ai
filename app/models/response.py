from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    decision: str = Field(..., description="Decision outcome: allow, block, require_hitl, log_and_allow")
    matched_rule: Optional[str] = Field(default=None, description="The ID of the rule that was matched, if any")
    reason: str = Field(..., description="The explanation or policy message for the decision")


class ExecutionResult(BaseModel):
    status: str = Field(..., description="Execution status description (e.g. executed, blocked, waiting_for_human)")
    decision: str = Field(..., description="The policy decision outcome")
    matched_rule: Optional[str] = Field(default=None, description="The matched rule ID")
    reason: Optional[str] = Field(default=None, description="The decision reason or rule message")
    tool_output: Optional[Dict[str, Any]] = Field(default=None, description="The raw output returned from executing the tool")
    correlation_id: Optional[str] = Field(default=None, description="Trace ID linking audit/history/metrics for this request")
    request_id: Optional[str] = Field(default=None, description="Unique ID for this API request")
    execution_id: Optional[str] = Field(default=None, description="Unique ID for this tool execution")


class ScenarioResult(BaseModel):
    scenario: str
    request: Dict[str, Any]
    decision: str
    matched_rule: Optional[str] = None
    reason: Optional[str] = None
    executed: bool
    tool_output: Dict[str, Any]


class DryRunResult(BaseModel):
    decision: str
    matched_rule: Optional[str] = None
    reason: Optional[str] = None
    would_execute: bool
    would_block: bool
    would_require_hitl: bool
    risk_level: str
    audit_preview: Dict[str, Any]
    simulated_output: Optional[Dict[str, Any]] = None


class SimulationResult(BaseModel):
    simulation: str = "completed"
    total_scenarios: int
    summary: Dict[str, int]
    results: List[ScenarioResult]
