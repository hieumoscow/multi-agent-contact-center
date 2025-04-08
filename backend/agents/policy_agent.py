from typing import Optional, Tuple
import json
from openai import AzureOpenAI
from managers.customer_manager import Customer
from managers.policy_manager import PolicyManager
from .core.base_agent import BaseAgent
from .core.agent_types import ConversationState, AgentType

class PolicyAgent(BaseAgent):
    def __init__(self, client: AzureOpenAI, policy_manager: PolicyManager):
        super().__init__(client)
        self.policy_manager = policy_manager
        self.agent_type = AgentType.POLICY_AGENT
        self.functions = [
            {
                "name": "get_policy_details",
                "description": "Get detailed information about a specific policy",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "policy_number": {
                            "type": "string",
                            "description": "The policy number (e.g., POL-123)"
                        }
                    },
                    "required": ["policy_number"]
                }
            },
            {
                "name": "list_policies",
                "description": "List all policies for the customer",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    def _get_policy_details(self, policy_number: str) -> str:
        """Get detailed information about a specific policy"""
        if policy_number not in self.policy_manager.policies:
            return f"Policy {policy_number} not found."
        return self.policy_manager.get_policy_details(policy_number)

    def _list_policies(self, customer: Optional[Customer]) -> str:
        """List all policies for the customer"""
        if not customer or not customer.policyNumbers:
            return "No policies found."
        policies = self.policy_manager.get_policies(customer.policyNumbers)
        summaries = "\n\n".join(self.policy_manager.format_policy_summary(p) for p in policies)
        return f"Here are your policies:\n\n{summaries}"

    def process_message(self, user_id: str, message: str, conv: ConversationState, customer: Optional[Customer] = None) -> Tuple[str, AgentType]:
        """Process policy-related messages"""
        if not customer:
            return "I apologize, but I cannot find your customer information. Please contact our support center for assistance.", self.agent_type

        # Format messages for the model
        messages = [
            {
                "role": "system",
                "content": f"""You are a policy assistant helping customers with insurance policy inquiries.
Available policies for this customer: {', '.join(customer.policyNumbers)}

Use the following functions:
- get_policy_details: Get detailed information about a specific policy
- list_policies: List all policies for the customer

If you can't find a specific policy number in the query but the user is asking about policy details, list all policies first."""
            },
            {"role": "user", "content": message}
        ]

        # Add conversation context if available
        if conv.last_summary:
            messages.insert(1, {"role": "system", "content": f"Previous conversation context: {conv.last_summary}"})

        # Get completion with function calling
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            functions=self.functions,
            function_call="auto",
            temperature=0
        )

        # Get the response message
        response_message = response.choices[0].message

        # Handle function calls
        if response_message.function_call:
            func_name = response_message.function_call.name
            func_args = json.loads(response_message.function_call.arguments)

            # Call the appropriate function
            if func_name == "get_policy_details":
                policy_info = self._get_policy_details(func_args["policy_number"])
            else:  # list_policies
                policy_info = self._list_policies(customer)

            # Get a natural language response
            messages.extend([
                {
                    "role": "assistant",
                    "content": None,
                    "function_call": {
                        "name": func_name,
                        "arguments": json.dumps(func_args)
                    }
                },
                {
                    "role": "function",
                    "name": func_name,
                    "content": policy_info
                }
            ])

            final_response = self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                temperature=0.7
            )

            return final_response.choices[0].message.content, self.agent_type
        else:
            return response_message.content, self.agent_type
