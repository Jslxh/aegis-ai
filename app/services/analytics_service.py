from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.repositories.analytics_repository import AnalyticsRepository
from app.database.repositories.policy_repository import PolicyRepository
from app.database.repositories.runtime_metric_repository import RuntimeMetricRepository


def _iso(value) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class AnalyticsService:
    """Dedicated analytics service. All queries hit PostgreSQL directly
    and use server-side aggregation (GROUP BY, window/aggregate functions)."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AnalyticsRepository(db)

    # ------------------------------------------------------------------
    # Core analytics (computed on-the-fly)
    # ------------------------------------------------------------------

    def policy_effectiveness(self, time_range: str = "30d") -> Dict[str, Any]:
        since = self._parse_range(time_range)
        items = self.repo.policy_effectiveness(since=since)
        return {
            "total_rules": len(items),
            "items": items,
        }

    def most_triggered_rules(self, time_range: str = "30d") -> Dict[str, Any]:
        since = self._parse_range(time_range)
        items = self.repo.most_triggered_rules(since=since)
        return {"items": items}

    def most_dangerous_tools(self, time_range: str = "30d") -> Dict[str, Any]:
        since = self._parse_range(time_range)
        items = self.repo.most_dangerous_tools(since=since)
        return {"items": items}

    def blocked_requests(self, time_range: str = "30d") -> Dict[str, Any]:
        since = self._parse_range(time_range)
        return self.repo.blocked_requests(since=since)

    def hitl_statistics(self, time_range: str = "30d") -> Dict[str, Any]:
        since = self._parse_range(time_range)
        return self.repo.hitl_statistics(since=since)

    def avg_response_time(self, time_range: str = "30d") -> Dict[str, Any]:
        since = self._parse_range(time_range)
        return self.repo.avg_response_time(since=since)

    def risk_distribution(self, time_range: str = "30d") -> Dict[str, Any]:
        since = self._parse_range(time_range)
        return self.repo.risk_distribution(since=since)

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def generate_daily_report(self, date: str) -> Dict[str, Any]:
        try:
            day = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid date. Expected format YYYY-MM-DD")

        start = day
        end = day + timedelta(days=1)

        data = self._build_report_data(start, end)
        data["period"] = date
        data["report_type"] = "daily"
        data["generated_at"] = _iso(datetime.utcnow())

        model = self.repo.upsert_report("daily", date, data)
        self.db.commit()
        return self._serialize_report(model)

    def generate_monthly_report(self, month: str) -> Dict[str, Any]:
        try:
            start = datetime.strptime(month, "%Y-%m")
        except ValueError:
            raise ValueError("Invalid month. Expected format YYYY-MM")

        if start.month == 12:
            end = datetime(start.year + 1, 1, 1)
        else:
            end = datetime(start.year, start.month + 1, 1)

        data = self._build_report_data(start, end)
        data["period"] = month
        data["report_type"] = "monthly"
        data["generated_at"] = _iso(datetime.utcnow())

        model = self.repo.upsert_report("monthly", month, data)
        self.db.commit()
        return self._serialize_report(model)

    def _build_report_data(self, start: datetime, end: datetime) -> Dict[str, Any]:
        return {
            "summary": self.repo.risk_distribution(since=start),
            "policy_effectiveness": self.repo.policy_effectiveness(since=start, limit=50),
            "most_triggered_rules": self.repo.most_triggered_rules(since=start, limit=25),
            "most_dangerous_tools": self.repo.most_dangerous_tools(since=start, limit=25),
            "blocked_requests": self.repo.blocked_requests(since=start),
            "hitl_statistics": self.repo.hitl_statistics(since=start),
            "response_time": self.repo.avg_response_time(since=start),
        }

    def get_report(self, report_type: str, period: str) -> Optional[Dict[str, Any]]:
        model = self.repo.find_report(report_type, period)
        if not model:
            return None
        return self._serialize_report(model)

    def list_reports(self, report_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        models = self.repo.list_reports(report_type=report_type, limit=limit)
        return [self._serialize_report(m) for m in models]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_range(self, time_range: str) -> Optional[datetime]:
        now = datetime.utcnow()
        if time_range == "1h":
            return now - timedelta(hours=1)
        elif time_range == "24h":
            return now - timedelta(hours=24)
        elif time_range == "7d":
            return now - timedelta(days=7)
        elif time_range == "30d":
            return now - timedelta(days=30)
        elif time_range == "all":
            return None
        return now - timedelta(days=30)

    def _serialize_report(self, model) -> Dict[str, Any]:
        return {
            "id": model.id,
            "report_type": model.report_type,
            "period": model.period,
            "generated_at": _iso(model.generated_at),
            "data": model.data,
        }
