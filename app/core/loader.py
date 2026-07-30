import os
import yaml
from typing import List, Dict, Any


class PolicyLoader:
    """Loads rules from configuration files."""

    def __init__(self, policy_file: str = None):
        if policy_file is None:
            if os.path.exists("configs/default.yaml"):
                policy_file = "configs/default.yaml"
            else:
                policy_file = "policies/default.yaml"
        self.policy_file = policy_file

    def load_rules(self) -> List[Dict[str, Any]]:
        with open(self.policy_file, "r") as file:
            data = yaml.safe_load(file)
            return data.get("rules", [])
