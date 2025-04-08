import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from azure.communication.chat import (
    ChatClient,
    CommunicationTokenCredential,
    ChatMessageType
)
from azure.core.exceptions import HttpResponseError
import json

@dataclass
class ChatEscalation:
    """Data class for chat escalation information"""
    customer_id: str
    customer_name: str
    chat_thread_id: str
    acs_identity: str
    messages: List[Dict]
    created_at: str
    status: str  # 'active' or 'closed'

    def dict(self):
        return asdict(self)

class EscalationManager:
    def __init__(self, chat_manager):
        self.chat_manager = chat_manager
        
        # Initialize escalations storage
        self.escalations_file = Path(__file__).parent.parent / "data" / "escalations.json"
        self.escalations: Dict[str, ChatEscalation] = {}
        self._load_escalations()
        
        self._chat_client = None
        self._token_expiry = None
        
    @property
    def chat_client(self) -> ChatClient:
        """Get a cached chat client, refreshing token if expired"""
        current_time = datetime.now()
        
        # Check if token is expired or about to expire in next 5 minutes
        if not self._chat_client or not self._token_expiry or current_time + timedelta(minutes=5) >= self._token_expiry:
            # Get new token
            token_result = self.chat_manager._get_chat_token()
            
            # Create new chat client
            self._chat_client = ChatClient(
                self.chat_manager.endpoint,
                CommunicationTokenCredential(token_result.token)
            )
            
            # Set token expiry (tokens typically valid for 24 hours)
            self._token_expiry = current_time + timedelta(hours=23)
            
        return self._chat_client

    def _load_escalations(self):
        """Load escalations from JSON file"""
        if self.escalations_file.exists():
            with open(self.escalations_file, "r") as f:
                data = json.load(f)
                self.escalations = {
                    thread_id: ChatEscalation(**escalation)
                    for thread_id, escalation in data.get("escalations", {}).items()
                }

    def _save_escalations(self):
        """Save escalations to JSON file"""
        # Convert escalations to dict format
        escalations_dict = {
            thread_id: escalation.dict()
            for thread_id, escalation in self.escalations.items()
        }
        
        # Create data directory if it doesn't exist
        self.escalations_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        with open(self.escalations_file, "w") as f:
            json.dump({"escalations": escalations_dict}, f, indent=4)

    def create_escalation(
        self,
        customer: "Customer",
        recent_messages: List[Dict[str, str]]
    ) -> Tuple[str, ChatEscalation]:
        """Create a new chat thread for escalation"""
        # Get ACS token for chat thread
        token_result = self.chat_manager._get_chat_token()
        chat_client = self.chat_client
        
        # Mask customer phone number with * and show the last 4 digits
        masked_phone = customer.phoneNumber[:-4] + "****"

        # Create new thread
        topic = f"Escalated Chat - Customer {customer.name} - {masked_phone}"
        create_thread_result = chat_client.create_chat_thread(topic)
        thread_id = create_thread_result.chat_thread.id
        
        # Add initial messages to thread using same client
        chat_thread_client = chat_client.get_chat_thread_client(thread_id)
        for msg in recent_messages:
            # Set display name based on role
            if msg["role"] == "user":
                sender_name = customer.name
            else:
                agent_type = msg.get("agent_type", "Customer Agent")
                if agent_type == "CUSTOMER_AGENT":
                    agent_type = "Customer Agent"
                elif agent_type == "CONTACT_CENTER":
                    agent_type = "Contact Center Agent"
                elif agent_type == "RELATIONSHIP_MANAGER":
                    agent_type = "Relationship Manager"
                sender_name = f"[{agent_type}]"
            
            chat_thread_client.send_message(
                content=msg["content"],
                sender_display_name=sender_name,
            )
            
        # Create escalation record
        escalation = ChatEscalation(
            customer_id=customer.phoneNumber,
            customer_name=customer.name,
            chat_thread_id=thread_id,
            acs_identity=token_result.token,
            messages=recent_messages,
            created_at=datetime.now().isoformat(),
            status="active"
        )
        
        # Save escalation
        self.escalations[thread_id] = escalation
        self._save_escalations()
        
        return thread_id, escalation

    def update_escalation(self, thread_id: str, message: str, role: str):
        """Update an escalation with a new message"""
        if thread_id not in self.escalations:
            raise ValueError(f"No escalation found for thread {thread_id}")
            
        escalation = self.escalations[thread_id]
        if escalation.status != "active":
            raise ValueError(f"Escalation {thread_id} is not active")
            
        try:
            # Add message to thread
            chat_thread_client = self.chat_client.get_chat_thread_client(thread_id)
            sender = "Customer" if role == "user" else "Assistant"
            chat_thread_client.send_message(
                content=message,
                sender_display_name=sender
            )
            
            # Update messages in escalation data
            escalation.messages.append({
                "role": role,
                "content": message
            })
        except HttpResponseError as e:
            if "TooManyRequests" in str(e):
                print(f"TooManyRequests error in update_escalation: {e}")
                raise ValueError("We are experiencing high traffic. Please try again in a few moments.")
            raise

    def update_escalation_messages(self, thread_id: str, messages: List[Dict]):
        """Update messages for an escalation"""
        if thread_id not in self.escalations:
            raise ValueError(f"No escalation found for thread {thread_id}")
            
        try:
            # Get chat thread client
            chat_thread_client = self.chat_client.get_chat_thread_client(thread_id)
            
            # Add each message to thread
            for msg in messages:
                sender = "Customer" if msg["role"] == "user" else "Assistant"
                chat_thread_client.send_message(
                    content=msg["content"],
                    sender_display_name=sender
                )
                
            # Update messages in escalation data
            self.escalations[thread_id].messages = messages
        except HttpResponseError as e:
            if "TooManyRequests" in str(e):
                print(f"TooManyRequests error in update_escalation_messages: {e}")
                raise ValueError("We are experiencing high traffic. Please try again in a few moments.")
            raise

    def disconnect_thread(self, thread_id: str):
        """Mark a chat thread as disconnected"""
        if thread_id not in self.escalations:
            raise ValueError(f"No escalation found for thread {thread_id}")
            
        try:
            # Add disconnect message to thread
            chat_thread_client = self.chat_client.get_chat_thread_client(thread_id)
            chat_thread_client.send_message(
                content="Customer has disconnected from the chat.",
                sender_display_name="System"
            )
            
            # Mark escalation as disconnected
            self.escalations[thread_id].status = "disconnected"
        except HttpResponseError as e:
            if "TooManyRequests" in str(e):
                print(f"TooManyRequests error in disconnect_thread: {e}")
                raise ValueError("We are experiencing high traffic. Please try again in a few moments.")
            raise

    def close_escalation(self, thread_id: str):
        """Mark an escalation as closed"""
        if thread_id in self.escalations:
            self.escalations[thread_id].status = "closed"
            self._save_escalations()
            print(f"Marked escalation {thread_id} as closed")

    def get_escalation(self, thread_id: str) -> Optional[ChatEscalation]:
        """Get escalation record by thread ID"""
        # Reload escalations to ensure we have latest data
        self._load_escalations()
        return self.escalations.get(thread_id)

    def get_active_escalation(self, customer_id: str) -> Optional[str]:
        """Get active escalation thread ID for a customer"""
        for thread_id, escalation in self.escalations.items():
            if escalation.customer_id == customer_id and escalation.status == "active":
                return thread_id
        return None
