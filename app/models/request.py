from typing import Optional, Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    tool: str = Field(..., description="The name of the target tool (e.g., database, email, file)")
    action: str = Field(..., description="The action to be performed (e.g., delete, send, read)")
    dry_run: Optional[bool] = Field(default=False, description="Flag for simulating execution without performing the actual action")

    def get_extra_fields(self) -> Dict[str, Any]:
        exclude_keys = {"tool", "action", "dry_run"}
        return {k: v for k, v in self.__dict__.items() if k not in exclude_keys}


class ExplainRequest(BaseModel):
    matched_rule: Optional[str] = None
    decision: str
    reason: str
    request: Dict[str, Any]
    execution_id: Optional[int] = None


class RiskAnalysisRequest(BaseModel):
    tool: str
    action: str
    parameters: Dict[str, Any]
    decision: str
    execution_id: Optional[int] = None


class HITLSummaryRequest(BaseModel):
    request: Dict[str, Any]
    decision: str
    reason: str


class AuditSummaryRequest(BaseModel):
    record: Dict[str, Any]
    audit_id: Optional[int] = None


class SimulationSummaryRequest(BaseModel):
    summary: Dict[str, int]
    results: List[Dict[str, Any]]
    simulation_id: Optional[int] = None
