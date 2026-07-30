from app.policy_engine import PolicyEngine


class Guardrail:

    def __init__(self):
        self.engine = PolicyEngine()

    def evaluate(self, request: dict):

        rules = self.engine.get_rules()

        for rule in rules:

            if (
                rule["tool"] == "database"
                and request["tool"] == "database"
                and rule["action"] == request["action"]
            ):
    
                condition = rule["condition"]["record_count"]

                if (
                    condition["operator"] == ">"
                    and request["record_count"] > condition["value"]
                ):
                    return {
                        "decision": rule["decision"],
                        "matched_rule": rule["id"],
                        "reason": rule["message"]
                    }

            elif (
                rule["tool"] == "email"
                and request["tool"] == "email"
                and request["external"] == True
            ):

                return {
                    "decision": rule["decision"],
                    "matched_rule": rule["id"],
                    "reason": rule["message"]
                }

            elif (
                rule["tool"] == "file"
                and request["tool"] == "file"
            ):

                keyword = rule["condition"]["path_contains"]

                if keyword in request["path"]:

                    return {
                        "decision": rule["decision"],
                        "matched_rule": rule["id"],
                        "reason": rule["message"]
                    }

        return {
                "decision":"allow",
                "matched_rule":None,
                "reason":"No matching policy. Action allowed."
        }