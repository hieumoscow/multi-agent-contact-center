from typing import List, Dict, Tuple, Optional
import os
from datetime import datetime
from openai import AzureOpenAI
from managers.customer_manager import CustomerManager, Customer
from managers.policy_manager import PolicyManager
from managers.chat_manager import ChatThreadManager
from managers.escalation_manager import EscalationManager
from .core.base_agent import BaseAgent
from .core.message_classifier import MessageClassifier
from .core.agent_types import AgentType, ConversationState
from .human_agent import HumanAgent

class CustomerAgent(BaseAgent):
    def __init__(self, openai_client: AzureOpenAI, customer_manager: CustomerManager, policy_manager: PolicyManager, chat_manager: ChatThreadManager, escalation_manager: EscalationManager):
        super().__init__(openai_client)
        self.customer_manager = customer_manager
        self.policy_manager = policy_manager
        self.chat_manager = chat_manager
        self.escalation_manager = escalation_manager
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if not deployment:
            raise ValueError("AZURE_OPENAI_DEPLOYMENT environment variable not set")
        self.classifier = MessageClassifier(openai_client, deployment)
        self.agent_type = AgentType.CUSTOMER_AGENT

    def _format_customer_info(self, customer: Customer) -> str:
        """Format customer information for display"""
        if not customer:
            return "No customer information available"
            
        return f"""Customer Information:
- Name: {customer.name}
- Customer ID: {customer.customerId}
- Policy Numbers: {', '.join(customer.policyNumbers)}
- Customer Type: {customer.customerType}
- Preferred Language: {customer.preferredLanguage}
- Email: {customer.email}
- Last Contact: {customer.lastContact}"""

    def _handle_identity_query(self, customer: Customer) -> str:
        """Handle who am I type queries"""
        return f"""Here is your information:
{self._format_customer_info(customer)}

How can I assist you today?"""

    def _handle_greeting(self, customer: Optional[Customer]) -> str:
        """Generate a personalized greeting using OpenAI"""
        current_time = datetime.now()
        
        if customer and customer.phoneNumber:  # Check if it's a registered customer
            prompt = f"""Generate a warm, personalized greeting for our customer for Contoso Insurance.
            Current time: {current_time}
            Customer info: {customer}
            Make it concise in a few lines, not like an email"""
            
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=1,
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        else:
            return "Hello there! \nThank you for reaching out to us. Please contact Hieu App GBB to access the ContosoAssist - WhatsApp Contact Center Service!"

    def _handle_help_query(self, customer: Customer) -> str:
        """Handle help/capability queries"""
        return f"""I'm your AI Insurance Assistant. Here's how I can help you:

1. Policy Information
   - Check your policy coverage
   - Explain policy benefits
   - Answer questions about claims
   - View your current policies

2. Account Services
   - View your customer information
   - Update contact preferences
   - Check policy status

3. Support Options
   - Connect you with a Contact Center Agent
   - Schedule a meeting with your Relationship Manager
   - Handle basic insurance queries

As a {customer.customerType} customer, you have {'priority' if customer.customerType == 'VIP' else 'standard'} access to our services.
How can I assist you today?"""

    def _handle_policy_query(self, customer: Customer, query: str) -> Optional[str]:
        """Handle basic policy queries"""
        policies = self.policy_manager.get_policies(customer.policyNumbers)
        if not policies:
            return "I don't see any active policies associated with your account. Would you like to speak with a representative about getting coverage?"
            
        # Check for policy number in query
        for policy in policies:
            if policy.policyNumber.lower() in query.lower() or policy.policyNumber.replace("POL-", "").lower() in query.lower():
                return self.policy_manager.get_policy_details(policy.policyNumber)
            
        # If asking about all policies
        if any(q in query.lower() for q in ["what policies", "my policies", "policy numbers", "which policies"]):
            summaries = "\n\n".join(self.policy_manager.format_policy_summary(p) for p in policies)
            return f"Here are your current policies:\n\n{summaries}\n\nWould you like to know more details about any specific policy?"
            
        return None

    def _should_escalate_to_rm(self, message: str, customer_type: str) -> bool:
        """Determine if query should be escalated to relationship manager"""
        result = self.classifier.classify_message(
            message,
            intents={"needs_rm": INTENT_NEEDS_RM}
        )
        return result == "needs_rm"

    def _should_escalate_to_contact_center(self, message: str, customer_type: str) -> bool:
        """Determine if query should be escalated to contact center"""
        result = self.classifier.classify_message(
            message,
            intents={"needs_agent": INTENT_NEEDS_AGENT}
        )
        return result == "needs_agent"

    def _get_intent(self, messages: List[Dict]) -> str:
        """Get the intent of the conversation"""
        # Format messages for the model
        formatted_messages = [
            {
                "role": "system",
                "content": """You are an intent classifier for a customer service system. 
                Analyze the conversation and determine if the customer needs to be connected to a human agent.
                Respond with one of:
                - ESCALATE: If the customer explicitly asks for a human agent or if the query is complex
                - CONTINUE: If the query can be handled by the AI
                """
            }
        ]
        
        # Add the last 5 messages for context
        for msg in messages[-5:]:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
            
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=formatted_messages,
            temperature=0,
            max_tokens=10
        )
        
        return response.choices[0].message.content.strip()

    def _get_conversation_summary(self, messages: List[Dict]) -> str:
        """Get a summary of the conversation"""
        formatted_messages = [
            {
                "role": "system",
                "content": "You are a conversation summarizer. Create a brief summary of the key points from this conversation."
            }
        ]
        
        # Add the last 20 messages for context
        for msg in messages[-20:]:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
            
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=formatted_messages,
            temperature=0.3,
            max_tokens=150
        )
        
        return response.choices[0].message.content.strip()

    def process_message(self, user_id: str, message: str, conv: ConversationState, customer: Optional[Customer] = None) -> Tuple[str, AgentType]:
        """Process a message from a user"""
        try:
            # Update customer info if available
            if customer and not conv.customer_info:
                conv.customer_info = self._format_customer_info(customer)
                
            # First check if message needs escalation
            human_agent = HumanAgent(self.client, self.deployment, self.chat_manager, self.escalation_manager)
            try:
                escalation_result = human_agent.check_and_handle_escalation(user_id, message, conv, customer)
                if escalation_result:
                    return escalation_result
            except ValueError as e:
                if "high traffic" in str(e):
                    # If we hit TooManyRequests, return a friendly message and stay with customer agent
                    return str(e), self.agent_type
                raise
        except Exception as e:
            return str(e), self.agent_type

        # If no escalation needed, handle as normal query
        return self._handle_general_query(user_id, message, customer, conv)

    def _handle_general_query(self, user_id: str, message: str, customer: Customer, conv: ConversationState) -> Tuple[str, AgentType]:
        """Handle general query"""
        # Handle other message types
        if "who am i" in message.lower() or "my info" in message.lower():
            return self._handle_identity_query(customer), AgentType.CUSTOMER_AGENT
        elif any(greeting in message.lower() for greeting in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]):
            return self._handle_greeting(customer), AgentType.CUSTOMER_AGENT
        elif "help" in message.lower() or "what can you do" in message.lower():
            return self._handle_help_query(customer), AgentType.CUSTOMER_AGENT

        # Try to handle policy queries
        policy_response = self._handle_policy_query(customer, message)
        if policy_response:
            return policy_response, AgentType.POLICY_AGENT

        # Handle general queries with context
        messages = [
            {"role": "system", "content": f"""You are an AI insurance assistant. Use this customer context in your responses:
{self._format_customer_info(customer)}

Try to answer questions directly using this information. Only suggest escalation if you really cannot help."""},
            {"role": "user", "content": message}
        ]
        
        if conv.last_summary:
            messages.insert(1, {"role": "system", "content": f"Previous conversation context: {conv.last_summary}"})
        
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )
        
        return response.choices[0].message.content, AgentType.CUSTOMER_AGENT
