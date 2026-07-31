from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, func
from app.database.session import Base


class RuntimeMetricModel(Base):
    __tablename__ = "runtime_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    tool = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    decision = Column(String(50), nullable=False)
    matched_rule = Column(String(255), nullable=True)
    reason = Column(String(500), nullable=True)
    execution_time_ms = Column(Float, nullable=False)
    tool_latency_ms = Column(Float, nullable=True)
    execution_status = Column(String(50), nullable=False)
    risk_level = Column(String(20), nullable=False)
    request_data = Column(JSON, nullable=True)
    tool_output = Column(JSON, nullable=True)
    user_id = Column(Integer, nullable=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    request_id = Column(String(100), nullable=True, index=True)
    execution_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
