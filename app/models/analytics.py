from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PolicyEffectivenessItem(BaseModel):
    rule_id: str
    total_matches: int
    blocked_count: int
    allowed_count: int
    hitl_count: int
    effectiveness_pct: float


class PolicyEffectivenessResult(BaseModel):
    total_rules: int
    items: List[PolicyEffectivenessItem]


class TriggeredRuleItem(BaseModel):
    rule_id: str
    trigger_count: int
    blocked_count: int
    tools_affected: int


class MostTriggeredRulesResult(BaseModel):
    items: List[TriggeredRuleItem]


class DangerousToolItem(BaseModel):
    tool: str
    total_requests: int
    blocked_count: int
    failure_count: int
    hitl_count: int
    avg_latency_ms: float
    block_rate_pct: float


class MostDangerousToolsResult(BaseModel):
    items: List[DangerousToolItem]


class BlockedRequestBreakdown(BaseModel):
    day: str
    blocked: int
    total: int


class BlockedRequestsResult(BaseModel):
    total_blocked: int
    total_requests: int
    block_rate_pct: float
    breakdown: List[BlockedRequestBreakdown]


class HITLStatisticsResult(BaseModel):
    total_requests: int
    pending: int
    approved: int
    rejected: int
    approval_rate_pct: float
    rejection_rate_pct: float
    avg_approval_time_hours: Optional[float] = None
    avg_resolution_time_hours: Optional[float] = None
    by_tool: Dict[str, int]


class ResponseTimeStats(BaseModel):
    avg_execution_time_ms: float
    min_execution_time_ms: float
    max_execution_time_ms: float
    median_execution_time_ms: float
    avg_tool_latency_ms: Optional[float] = None
    total_requests: int
    by_tool: List[Dict[str, Any]]


class RiskDistributionItem(BaseModel):
    risk_level: str
    count: int
    percentage: float


class RiskDistributionResult(BaseModel):
    items: List[RiskDistributionItem]
    total: int


class AnalyticsReport(BaseModel):
    report_type: str
    period: str
    generated_at: str
    data: Dict[str, Any]


class AnalyticsReportResponse(BaseModel):
    id: int
    report_type: str
    period: str
    generated_at: str
    data: Dict[str, Any]
