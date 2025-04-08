from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Message:
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = datetime.now()

# This class is deprecated - use agents.agent_types.ConversationState instead
# @dataclass
# class ConversationState:
#     messages: List[Message]
#     chat_thread_id: Optional[str] = None
#     
#     def __init__(self):
#         self.messages = []
#         self.chat_thread_id = None
#         
#     def add_message(self, role: str, content: str):
#         """Add a new message to the conversation"""
#         self.messages.append(Message(role=role, content=content))
#         
#     def get_last_message(self) -> Optional[Message]:
#         """Get the last message in the conversation"""
#         return self.messages[-1] if self.messages else None
