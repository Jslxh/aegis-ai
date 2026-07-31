from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.database.models.simulation_run import SimulationRunModel
from app.database.repositories.base import BaseRepository


class SimulationRunRepository(BaseRepository[SimulationRunModel]):
    def __init__(self, session: Session):
        super().__init__(session, SimulationRunModel)

    def create_run(
        self,
        total_scenarios: int,
        summary: Dict[str, int],
        results: List[Dict[str, Any]],
    ) -> SimulationRunModel:
        model = SimulationRunModel(
            total_scenarios=total_scenarios,
            summary=summary,
            results=results,
        )
        return self.add(model)

    def list_recent(self, limit: int = 20) -> List[SimulationRunModel]:
        return (
            self.session.query(SimulationRunModel)
            .order_by(SimulationRunModel.created_at.desc())
            .limit(limit)
            .all()
        )
