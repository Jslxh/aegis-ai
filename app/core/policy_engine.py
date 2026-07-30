from typing import List, Dict, Any
from .loader import PolicyLoader


class PolicyEngine:
    """Manages loaded policies for evaluation."""

    def __init__(self, policy_file: str = None):
        self.loader = PolicyLoader(policy_file)
        self.rules = self.loader.load_rules()

    def get_rules(self) -> List[Dict[str, Any]]:
        # Enable hot-reloading by reading loader dynamically
        return self.loader.load_rules()
