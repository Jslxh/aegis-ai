from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, func
from app.database.session import Base


class PolicyModel(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String(255), unique=True, nullable=False, index=True)
    tool = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    conditions = Column(JSON, nullable=False, default=list)
    combinator = Column(String(10), nullable=False, default="AND")
    decision = Column(String(50), nullable=False)
    message = Column(String(500), nullable=False)
    priority = Column(Integer, nullable=False, default=0)
    version = Column(Integer, nullable=False, default=1)
    enabled = Column(Boolean, nullable=False, default=True)
    tags = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
