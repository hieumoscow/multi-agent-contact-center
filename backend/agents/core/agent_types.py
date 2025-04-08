from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

class AgentType(str, Enum):
    USER = "user"
    CUSTOMER_AGENT = "customer_agent"
    POLICY_AGENT = "policy_agent"
    CONTACT_CENTER = "contact_center"
    RELATIONSHIP_MANAGER = "relationship_manager"
    
    @property
    def display_name(self) -> str:
        return {
            AgentType.USER: "Customer",
            AgentType.CUSTOMER_AGENT: "Customer Service",
            AgentType.POLICY_AGENT: "Policy Specialist",
            AgentType.CONTACT_CENTER: "Contact Center",
            AgentType.RELATIONSHIP_MANAGER: "Relationship Manager"
        }[self]

@dataclass
class Message:
    role: str
    content: str
    agent_type: AgentType = AgentType.USER
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ConversationState:
    messages: List[Message] = field(default_factory=list)
    current_agent: AgentType = AgentType.CUSTOMER_AGENT
    last_summary: Optional[str] = None
    policy_checked: bool = False
    customer_info: Optional[str] = None
    chat_thread_id: Optional[str] = None
