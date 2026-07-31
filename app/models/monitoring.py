from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MetricSummary(BaseModel):
    total_requests: int = 0
    blocked_count: int = 0
    allowed_count: int = 0
    hitl_count: int = 0
    log_and_allow_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_execution_time_ms: float = 0.0
    avg_tool_latency_ms: Optional[float] = None


class TimelinePoint(BaseModel):
    timestamp: str
    total: int
    blocked: int
    allowed: int
    failed: int


class MetricTimeline(BaseModel):
    granularity: str
    points: List[TimelinePoint]


class RecentActivityItem(BaseModel):
    id: int
    timestamp: str
    tool: str
    action: str
    decision: str
    matched_rule: Optional[str] = None
    execution_status: str
    execution_time_ms: float
    risk_level: str


class ViolationItem(BaseModel):
    matched_rule: str
    count: int
    last_occurrence: str
    tool: Optional[str] = None
    action: Optional[str] = None


class DashboardStats(BaseModel):
    total_requests: int
    blocked_count: int
    success_rate: float
    avg_execution_time_ms: float
    active_rules_count: int
    top_risk_level: str
    recent_activity: List[RecentActivityItem]


class RuntimeMetricResponse(BaseModel):
    id: int
    timestamp: str
    tool: str
    action: str
    decision: str
    matched_rule: Optional[str] = None
    reason: Optional[str] = None
    execution_time_ms: float
    tool_latency_ms: Optional[float] = None
    execution_status: str
    risk_level: str
    request_data: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None


class MonitoringConfig(BaseModel):
    enabled: bool = Field(default=True, description="Enable runtime monitoring")
    detailed_logging: bool = Field(default=False, description="Log full request/response data")
