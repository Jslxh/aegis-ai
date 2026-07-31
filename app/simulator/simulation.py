from typing import Optional, Any, Dict
from sqlalchemy.orm import Session
from app.core.guardrail import Guardrail
from app.core.executor import ToolExecutor
from app.audit.logger import AuditLogger, PostgresAuditLogger


class Simulation:
    """Simulation harness to run test scenarios showing all guardrail policy outcomes."""

    def __init__(self, session_factory: Optional[callable] = None):
        self.guardrail = Guardrail()
        self.executor = ToolExecutor()
        self.audit = PostgresAuditLogger(session_factory) if session_factory else AuditLogger()
        self.session_factory = session_factory

    def _persist_run(self, result: Dict[str, Any]) -> None:
        if not self.session_factory:
            return
        from app.database.repositories.simulation_run_repository import SimulationRunRepository

        session: Session = self.session_factory()
        try:
            repo = SimulationRunRepository(session)
            repo.create_run(
                total_scenarios=result["total_scenarios"],
                summary=result["summary"],
                results=result["results"],
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def run(self) -> dict:
        scenarios = [
            {
                "name": "Large Delete",
                "tool": "database",
                "action": "delete",
                "record_count": 500
            },
            {
                "name": "Small Delete",
                "tool": "database",
                "action": "delete",
                "record_count": 5
            },
            {
                "name": "External Email",
                "tool": "email",
                "action": "send",
                "external": True,
                "recipient": "user@gmail.com"
            },
            {
                "name": "Internal Email",
                "tool": "email",
                "action": "send",
                "external": False,
                "recipient": "employee@company.com"
            },
            {
                "name": "Confidential File",
                "tool": "file",
                "action": "read",
                "path": "documents/confidential_salary.pdf"
            }
        ]

        results = []
        blocked = 0
        hitl = 0
        allowed = 0
        logged = 0

        for request in scenarios:
            decision = self.guardrail.evaluate(request)
            self.audit.log(request, decision)

            if decision["decision"] == "block":
                blocked += 1
                output = {
                    "status": "Blocked by Guardrail"
                }
            elif decision["decision"] == "require_hitl":
                hitl += 1
                output = {
                    "status": "Pending Human Approval"
                }
            elif decision["decision"] == "log_and_allow":
                logged += 1
                output = self.executor.execute(request)
            else:
                allowed += 1
                output = self.executor.execute(request)

            results.append({
                "scenario": request["name"],
                "request": request,
                "decision": decision["decision"],
                "matched_rule": decision.get("matched_rule"),
                "reason": decision.get("reason"),
                "executed": decision["decision"] in ["allow", "log_and_allow"],
                "tool_output": output
            })

        result = {
            "simulation": "completed",
            "total_scenarios": len(results),
            "summary": {
                "blocked": blocked,
                "require_hitl": hitl,
                "allowed": allowed,
                "log_and_allow": logged
            },
            "results": results
        }

        self._persist_run(result)
        return result
