from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field
from datetime import datetime


class PolicyCreate(BaseModel):
    rule_id: str = Field(..., description="Unique rule identifier")
    tool: str = Field(..., description="Target tool (e.g. database, email, file)")
    action: str = Field(..., description="Action to guard (e.g. delete, send, read)")
    conditions: List[Dict[str, Any]] = Field(default=[], description="List of condition objects with field/operator/value")
    combinator: str = Field(default="AND", description="Condition combinator: AND or OR")
    decision: str = Field(..., description="Decision outcome: allow, block, require_hitl, log_and_allow")
    message: str = Field(..., description="Policy message / reason")
    priority: int = Field(default=0, ge=0, description="Evaluation priority (higher = evaluated first)")
    enabled: bool = Field(default=True, description="Whether this policy is active")
    tags: Optional[List[str]] = Field(default=None, description="Arbitrary tags for categorization")


class PolicyUpdate(BaseModel):
    tool: Optional[str] = None
    action: Optional[str] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    combinator: Optional[str] = None
    decision: Optional[str] = None
    message: Optional[str] = None
    priority: Optional[int] = Field(default=None, ge=0)
    enabled: Optional[bool] = None
    tags: Optional[List[str]] = None


class PolicyResponse(BaseModel):
    id: int
    rule_id: str
    tool: str
    action: str
    conditions: List[Dict[str, Any]]
    combinator: str
    decision: str
    message: str
    priority: int
    version: int
    enabled: bool
    tags: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PolicyConflict(BaseModel):
    existing_policy_id: int
    existing_rule_id: str
    field: str
    description: str


class PolicyValidationResult(BaseModel):
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class RulePreviewRequest(BaseModel):
    policy: PolicyCreate
    request: Dict[str, Any]


class RulePreviewResult(BaseModel):
    would_match: bool
    decision: str
    message: str
    reason: str


class PolicyExportResult(BaseModel):
    policies: List[Dict[str, Any]]
    format: str = "yaml"
