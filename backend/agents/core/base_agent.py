from typing import Optional
import os
from datetime import datetime
from openai import AzureOpenAI
from managers.customer_manager import Customer
from .agent_types import ConversationState

class BaseAgent:
    def __init__(self, client: AzureOpenAI):
        """Initialize base agent"""
        self.client = client
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if not self.deployment:
            raise ValueError("AZURE_OPENAI_DEPLOYMENT environment variable is not set")

    def process_message(self, user_id: str, message: str, conv: ConversationState, customer: Optional[Customer] = None) -> str:
        """Process a message"""
        raise NotImplementedError("Subclasses must implement process_message")
