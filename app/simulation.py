from app.guardrail import Guardrail
from app.executor import ToolExecutor
from app.audit import AuditLogger


class Simulation:

    def __init__(self):
        self.guardrail = Guardrail()
        self.executor = ToolExecutor()
        self.audit = AuditLogger()

    def run(self):

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

            # Step 1: Evaluate action
            decision = self.guardrail.evaluate(request)

            # Step 2: Audit every evaluated action
            self.audit.log(request, decision)

            # Step 3: Execute based on decision
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

                "executed": decision["decision"] in [
                    "allow",
                    "log_and_allow"
                ],

                "tool_output": output

            })

        return {

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