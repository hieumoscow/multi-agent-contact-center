from typing import Dict, Optional, Tuple, List
import json
import sys
import os

# Add backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import AzureOpenAI
from managers.customer_manager import Customer
from managers.chat_manager import ChatThreadManager
from managers.escalation_manager import EscalationManager
from .core.message_classifier import MessageClassifier
from .core.base_agent import BaseAgent
from .core.agent_types import AgentType, ConversationState
from .core.intents import DISCONNECT_INTENTS

class HumanAgent(BaseAgent):
    def __init__(self, client: AzureOpenAI, deployment: str, chat_manager: ChatThreadManager, escalation_manager: EscalationManager):
        super().__init__(client)
        self.chat_manager = chat_manager
        self.escalation_manager = escalation_manager
        self.classifier = MessageClassifier(client, deployment)
        self.agent_type = AgentType.CONTACT_CENTER

    def process_message(self, user_id: str, message: str, conv: ConversationState, customer: Optional[Customer] = None) -> str:
        """Process a message in a human agent conversation"""
        # Update escalation with user message
        if conv.chat_thread_id:
            self.escalation_manager.update_escalation(conv.chat_thread_id, message, "user")
        
        # Convert intents to dictionary format
        intents = {
            intent.name: intent.examples
            for intent in DISCONNECT_INTENTS
        }
        
        # Classify message against disconnect intents
        result = self.classifier.classify_message(
            message, 
            intents=intents,
            conversation=conv
        )
        
        # Handle disconnect flow
        if result == "wants_disconnect":
            return self.handle_disconnect(user_id, conv)[0]
            
        # Handle confirmation of disconnect
        if result == "confirms_disconnect":
            return self.handle_disconnect(user_id, conv, is_confirmation=True)[0]
            
        # For normal messages, just record in chat thread without responding
        return None

    def process_media(self, user_id: str, media_type: str, filepath: str, conv: ConversationState) -> str:
        """Process a media message in a human agent conversation"""
        message = f"[Received {media_type}: {filepath}]"
        
        # Add media message to thread if we have one
        if conv.chat_thread_id:
            self.escalation_manager.update_escalation(conv.chat_thread_id, message, "user")

        # Default acknowledgment
        response = f"I've received your {media_type}. A human agent will review it shortly."
        if conv.chat_thread_id:
            self.escalation_manager.update_escalation(conv.chat_thread_id, response, "assistant")
        return response

    def check_and_handle_escalation(self, user_id: str, message: str, conv: ConversationState, customer: Optional[Customer] = None) -> Optional[Tuple[str, AgentType]]:
        """Check if message requires escalation and handle it if needed"""
        # Get classification
        intent = self.classifier.classify_message(message, conv)
        
        # Handle based on intent
        if intent == "wants_disconnect":
            return self.handle_disconnect(user_id, conv)
        elif intent == "confirms_disconnect":
            return self.handle_disconnect(user_id, conv, is_confirmation=True)
        elif intent == "needs_agent":
            return self.handle_escalation(user_id, message, conv, customer, AgentType.CONTACT_CENTER)
        elif intent == "needs_rm":
            return self.handle_escalation(user_id, message, conv, customer, AgentType.RELATIONSHIP_MANAGER)
            
        return None  # No escalation needed

    def handle_escalation(self, user_id: str, message: str, conv: ConversationState, customer: Optional[Customer] = None, escalation_type: AgentType = AgentType.CONTACT_CENTER) -> Tuple[str, AgentType]:
        """Handle escalation to human agent (either Contact Center or RM)"""
        try:
            # Get conversation summary if we have messages
            summary = ""
            if conv.messages:
                summary = self._get_conversation_summary([{"role": m.role, "content": m.content} for m in conv.messages])
            
            # Create chat thread for escalation if not exists
            if not conv.chat_thread_id:
                thread_id, escalation = self.escalation_manager.create_escalation(
                    customer=customer,
                    recent_messages=[{"role": m.role, "content": m.content} for m in conv.messages[-20:]] if conv.messages else []
                )
                conv.chat_thread_id = thread_id
                conv.last_summary = summary

            # Add system message about escalation
            if escalation_type == AgentType.RELATIONSHIP_MANAGER:
                response = (
                    f"As a VIP customer, I'll connect you with your dedicated Relationship Manager.\n\n"
                    f"Chat Thread URL: https://hieuacschat.azurewebsites.net?threadId={conv.chat_thread_id}\n"
                    f"Summary of conversation:\n{summary}"
                )
            else:
                response = (
                    f"I'll connect you with our Contact Center Agent right away.\n\n"
                    f"Chat Thread URL: https://hieuacschat.azurewebsites.net?threadId={conv.chat_thread_id}\n"
                    f"Summary of conversation:\n{summary}\n\n"
                    f"You can type 'disconnect' at any time to end the conversation.\n"
                    "A human agent will be with you shortly."
                )

            # Update escalation with the response
            try:
                self.escalation_manager.update_escalation_messages(
                    conv.chat_thread_id,
                    [{"role": m.role, "content": m.content} for m in conv.messages] + 
                    [{"role": "assistant", "content": response}] if conv.messages else [{"role": "assistant", "content": response}]
                )
            except ValueError as e:
                if "high traffic" in str(e):
                    # If we hit TooManyRequests, pass the error up
                    raise
                
            # Return escalation message
            return response, escalation_type
        except ValueError as e:
            if "high traffic" in str(e):
                raise
            print(f"Error in handle_escalation: {e}")
            return str(e), AgentType.CUSTOMER_AGENT

    def handle_disconnect(self, user_id: str, conv: ConversationState, is_confirmation: bool = False) -> Tuple[str, AgentType]:
        """Handle disconnect request or confirmation"""
        if not conv.chat_thread_id:
            return "You are not currently in an active chat session.", AgentType.CUSTOMER_AGENT

        if is_confirmation:
            # User confirmed they want to disconnect
            self.escalation_manager.disconnect_thread(conv.chat_thread_id)
            response = "Thank you for chatting with us today. Have a great day!"
            conv.chat_thread_id = None
            conv.current_agent = AgentType.CUSTOMER_AGENT
            return response, AgentType.CUSTOMER_AGENT
        else:
            # Ask for confirmation
            response = "Thank you for chatting with us today. Is there anything else you need help with before you go?"
            self.escalation_manager.update_escalation(conv.chat_thread_id, response, "assistant")
            return response, conv.current_agent

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
