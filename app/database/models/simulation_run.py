from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, JSON, func
from app.database.session import Base


class SimulationRunModel(Base):
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    total_scenarios = Column(Integer, nullable=False)
    summary = Column(JSON, nullable=False)
    results = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
