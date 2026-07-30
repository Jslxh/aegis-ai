import json
from datetime import datetime


class AuditLogger:

    def __init__(self):
        self.file = "logs/audit.log"

    def log(self, request, decision):

        record = {

            "timestamp": datetime.now().isoformat(),

            "tool": request["tool"],

            "action": request["action"],

            "request": request,

            "decision": decision["decision"],

            "matched_rule": decision["matched_rule"],

            "reason": decision["reason"]

        }

        with open(self.file, "a") as f:
            f.write(json.dumps(record))
            f.write("\n")