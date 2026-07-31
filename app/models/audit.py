from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AuditRecord(BaseModel):
    id: int
    timestamp: Optional[str] = None
    event_type: Optional[str] = None
    status: Optional[str] = None
    tool: str
    action: str
    request_data: Optional[Dict[str, Any]] = None
    decision: str
    matched_rule: Optional[str] = None
    reason: Optional[str] = None
    risk_level: Optional[str] = None
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    execution_id: Optional[str] = None
    source: Optional[str] = None
    actor: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    checksum: Optional[str] = None
    prev_checksum: Optional[str] = None


class AuditSearchResult(BaseModel):
    items: List[AuditRecord]
    total: int
    page: int
    page_size: int
    pages: int


class AuditTimelinePoint(BaseModel):
    bucket: str
    total: int
    decisions: Dict[str, int]


class AuditTimelineResult(BaseModel):
    granularity: str
    points: List[AuditTimelinePoint]


class IntegrityResult(BaseModel):
    valid: bool
    checked: int
    errors: List[str]
