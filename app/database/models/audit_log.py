from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, func
from app.database.session import Base


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)
    event_type = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True)
    tool = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    request_data = Column(JSON, nullable=False)
    decision = Column(String(50), nullable=False)
    matched_rule = Column(String(255), nullable=True)
    reason = Column(String(500), nullable=True)
    risk_level = Column(String(20), nullable=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    request_id = Column(String(100), nullable=True, index=True)
    execution_id = Column(String(100), nullable=True, index=True)
    source = Column(String(50), nullable=True)
    actor = Column(String(100), nullable=True)
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    checksum = Column(String(64), nullable=True)
    prev_checksum = Column(String(64), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
