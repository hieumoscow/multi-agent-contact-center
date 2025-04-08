from typing import Dict
import os
from openai import AzureOpenAI
from managers.customer_manager import CustomerManager
from managers.policy_manager import PolicyManager
from managers.chat_manager import ChatThreadManager
from managers.escalation_manager import EscalationManager
from .customer_agent import CustomerAgent
from .policy_agent import PolicyAgent
from .human_agent import HumanAgent
from .core.agent_types import AgentType, Message, ConversationState

class AgentManager:
    def __init__(self):
        # Initialize OpenAI client
        self.openai_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
        # Initialize managers
        self.customer_manager = CustomerManager()
        self.policy_manager = PolicyManager()
        self.chat_manager = ChatThreadManager()
        self.escalation_manager = EscalationManager(self.chat_manager)
        
        # Initialize agents
        self.customer_agent = CustomerAgent(
            self.openai_client,
            self.customer_manager,
            self.policy_manager,
            self.chat_manager,
            self.escalation_manager
        )
        self.human_agent = HumanAgent(
            self.openai_client,
            self.deployment,
            self.chat_manager,
            self.escalation_manager
        )
        
        # Store conversations
        self.conversations: Dict[str, ConversationState] = {}
        
    def _get_or_create_conversation(self, user_id: str) -> ConversationState:
        """Get existing conversation or create new one"""
        if user_id not in self.conversations:
            # Get customer info if available
            customer = self.customer_manager.get_customer(user_id)
            customer_info = self.customer_agent._format_customer_info(customer) if customer else None
            
            # Create new conversation state
            self.conversations[user_id] = ConversationState(
                messages=[],
                current_agent=AgentType.CUSTOMER_AGENT,
                customer_info=customer_info,
                chat_thread_id=None
            )
            
        return self.conversations[user_id]
        
    def process_message(self, user_id: str, message: str) -> str:
        """Process a message from a user"""
        try:
            # Get or create conversation state
            conv = self._get_or_create_conversation(user_id)
            
            # Get customer if available
            customer = self.customer_manager.get_customer(user_id)
            if customer and not conv.customer_info:
                conv.customer_info = self.customer_agent._format_customer_info(customer)
            
            # Add user message to history
            conv.messages.append(Message(role="user", content=message))
            
            # Process message based on current agent
            response = None
            next_agent = conv.current_agent
            print(f"Current agent: {conv.current_agent}")
            
            # If in contact center chat, let human agent handle it
            if conv.current_agent == AgentType.CONTACT_CENTER:
                response = self.human_agent.process_message(user_id, message, conv, customer)
                # Get next agent from conversation state since HumanAgent updates it directly
                next_agent = conv.current_agent
            else:
                # Route everything through customer agent
                response, next_agent = self.customer_agent.process_message(user_id, message, conv, customer)
                
            # Handle agent transition
            if next_agent != conv.current_agent:
                conv.current_agent = next_agent
                
            # Add response to history if we got one
            if response:
                msg = Message(role="assistant", content=response, agent_type=conv.current_agent)
                conv.messages.append(msg)
                
                try:
                    # Update thread if exists
                    if conv.chat_thread_id:
                        self.escalation_manager.update_escalation(conv.chat_thread_id, response, "assistant")
                except Exception as e:
                    if "TooManyRequests" in str(e):
                        # Return the error message to the user
                        return str(e)
                    else:
                        raise
                        
            return response
            
        except Exception as e:
            print(f"Error processing message: {e}")
            raise

    def process_media(self, user_id: str, media_type: str, filepath: str) -> str:
        """Process a media message from a user"""
        # Get or create conversation state
        conv = self._get_or_create_conversation(user_id)
        
        # Add media message to history
        conv.messages.append(Message(role="user", content=f"[Sent {media_type}]"))
        
        # Process based on current agent
        response = None
        if conv.current_agent == AgentType.CONTACT_CENTER:
            response = self.human_agent.process_media(user_id, media_type, filepath, conv)
        else:
            # For non-human agents, always escalate media to contact center
            response, next_agent = self.human_agent.handle_escalation(user_id, f"[Sent {media_type}]", conv, None, AgentType.CONTACT_CENTER)
            conv.current_agent = next_agent
            
        # Add response to history
        if response:
            conv.messages.append(Message(role="assistant", content=response, agent_type=conv.current_agent))
            
        return f"[{conv.current_agent.display_name}] {response}" if response else None
