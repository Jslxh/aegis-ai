from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, JSON, func
from app.database.session import Base


class AnalyticsReportModel(Base):
    __tablename__ = "analytics_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(20), nullable=False)
    period = Column(String(20), nullable=False)
    data = Column(JSON, nullable=False)
    generated_at = Column(DateTime, server_default=func.now(), nullable=False)
