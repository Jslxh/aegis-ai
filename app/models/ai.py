from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class AIGeneratedContentResponse(BaseModel):
    id: int
    content_type: str
    source_type: str
    source_id: int
    tool: Optional[str] = None
    action: Optional[str] = None
    decision: Optional[str] = None
    matched_rule: Optional[str] = None
    explanation: Optional[str] = None
    risk_analysis: Optional[str] = None
    risk_level: Optional[str] = None
    recommendations: Optional[List[str]] = None
    confidence: Optional[float] = None
    summary: Optional[str] = None
    model: Optional[str] = None
    latency_ms: Optional[float] = None
    created_at: Optional[str] = None


class AIGenerationResult(BaseModel):
    success: bool
    content: Optional[str] = None
    model: Optional[str] = None
    latency: Optional[float] = None
    explanation: Optional[str] = None
    risk_analysis: Optional[str] = None
    risk_level: Optional[str] = None
    recommendations: Optional[List[str]] = None
    confidence: Optional[float] = None
    summary: Optional[str] = None
    error: Optional[str] = None
