import yaml


class PolicyEngine:

    def __init__(self, policy_file="policies/default.yaml"):
        with open(policy_file, "r") as file:
            self.policies = yaml.safe_load(file)["rules"]

    def get_rules(self):
        return self.policies