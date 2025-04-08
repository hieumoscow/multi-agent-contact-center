import json
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Policy:
    """Raw policy data class"""
    data: Dict[str, Any]

    def __getattr__(self, name):
        """Allow accessing policy data as attributes"""
        return self.data.get(name)

    @property
    def policyNumber(self):
        return self.data.get("policyNumber")

class PolicyManager:
    def __init__(self):
        self.policies = {}
        self._load_policies()

    def _load_policies(self):
        """Load policies from JSON file"""
        # Go up one level from managers to backend, then to data
        policy_file = Path(__file__).parent.parent / "data" / "policies.json"
        with open(policy_file, 'r') as f:
            data = json.load(f)
            policies_data = data.get("policies", {})
            self.policies = {
                policy_number: Policy(policy_data)
                for policy_number, policy_data in policies_data.items()
            }

    def get_policies(self, policy_numbers: List[str]) -> List[Policy]:
        """Get policies by their numbers"""
        return [self.policies[num] for num in policy_numbers if num in self.policies]

    def format_policy_summary(self, policy: Policy) -> str:
        """Format a brief summary of a policy"""
        return f"""Policy {policy.policyNumber} - {policy.name} ({policy.type})
Coverage Amount: ${policy.coverageAmount:,}
Premium: ${policy.premium['amount']:,}/{policy.premium['frequency']}
Status: {policy.status}"""

    def format_policy_details(self, policy: Policy) -> str:
        """Format detailed policy information"""
        benefits = "\n".join(f"- {benefit}" for benefit in policy.benefits)
        exclusions = "\n".join(f"- {exclusion}" for exclusion in policy.exclusions)
        riders = "\n".join(f"- {rider['name']}: {rider['coverage']}" for rider in policy.riders)
        
        return f"""Policy Details for {policy.policyNumber} - {policy.name}
Type: {policy.type}
Coverage Amount: ${policy.coverageAmount:,}
Premium: ${policy.premium['amount']:,} {policy.premium['frequency']}
Status: {policy.status}

Benefits:
{benefits}

Exclusions:
{exclusions}

Additional Riders:
{riders}

Policy Period: {policy.startDate} to {policy.endDate}
Waiting Period: {policy.waitingPeriod}

Claim Process:
{policy.claimProcess}"""

    def get_policy_details(self, policy_number: str) -> str:
        """Get formatted details for a specific policy"""
        if policy_number not in self.policies:
            return f"Policy {policy_number} not found."
        return self.format_policy_details(self.policies[policy_number])