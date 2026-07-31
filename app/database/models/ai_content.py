from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Text, func
from app.database.session import Base


class AIGeneratedContentModel(Base):
    __tablename__ = "ai_generated_content"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content_type = Column(String(50), nullable=False)
    source_type = Column(String(50), nullable=False)
    source_id = Column(Integer, nullable=False)
    tool = Column(String(100), nullable=True)
    action = Column(String(100), nullable=True)
    decision = Column(String(50), nullable=True)
    matched_rule = Column(String(255), nullable=True)
    explanation = Column(Text, nullable=True)
    risk_analysis = Column(Text, nullable=True)
    risk_level = Column(String(20), nullable=True)
    recommendations = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)
    model = Column(String(100), nullable=True)
    latency_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
