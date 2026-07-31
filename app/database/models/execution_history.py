from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, JSON, func
from app.database.session import Base


class ExecutionHistoryModel(Base):
    __tablename__ = "execution_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tool = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    request_data = Column(JSON, nullable=False)
    decision = Column(String(50), nullable=False)
    matched_rule = Column(String(255), nullable=True)
    reason = Column(String(500), nullable=True)
    execution_status = Column(String(50), nullable=False)
    tool_output = Column(JSON, nullable=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    request_id = Column(String(100), nullable=True, index=True)
    execution_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
