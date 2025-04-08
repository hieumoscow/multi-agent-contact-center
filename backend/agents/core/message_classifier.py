from typing import Optional, Dict, List
import json
from openai import AzureOpenAI
from .agent_types import ConversationState

class Intent:
    def __init__(self, name: str, description: str, examples: List[str]):
        """
        Define an intent to classify messages against
        
        Args:
            name: Unique identifier for the intent
            description: Clear description of what this intent means
            examples: List of example phrases that match this intent
        """
        self.name = name
        self.description = description
        self.examples = examples

class MessageClassifier:
    def __init__(self, client: AzureOpenAI, deployment: str):
        self.client = client
        self.deployment = deployment
        
    def classify_message(
        self,
        message: str,
        conversation: Optional[ConversationState] = None,
        intents: Optional[Dict[str, List[str]]] = None
    ) -> str:
        """Classify a message into an intent"""
        # Use default intents if none provided
        if not intents:
            intents = {
                "wants_disconnect": [
                    "I want to disconnect",
                    "Please end this chat",
                    "Close this conversation",
                    "End chat",
                    "Bye",
                    "Goodbye"
                ],
                "confirms_disconnect": [
                    "Yes, please disconnect",
                    "Yes, end the chat",
                    "Yes, close the conversation",
                    "Yes, goodbye",
                    "Confirm disconnect"
                ],
                "needs_agent": [
                    "I need to speak with a human",
                    "Connect me to an agent",
                    "Talk to customer service",
                    "Speak with representative",
                    "Talk to human"
                ],
                "needs_rm": [
                    "I need my relationship manager",
                    "Connect me to my RM",
                    "Speak with relationship manager",
                    "Talk to RM"
                ]
            }
            
        # Format conversation context
        context = ""
        if conversation:
            messages = []
            if isinstance(conversation, list):
                messages = conversation
            elif hasattr(conversation, 'messages'):
                messages = conversation.messages
                
            if messages:
                context = "\n".join([
                    f"{msg.role}: {msg.content}"
                    for msg in messages[-5:]  # Last 5 messages
                ])
            
        # Create prompt
        prompt = f"""Given the following message and conversation context, classify the message into one of these intents: {list(intents.keys())}

Example messages for each intent:
{json.dumps(intents, indent=2)}

Conversation context:
{context}

Message to classify:
{message}

Return ONLY the intent name, nothing else. If no intent matches, return "general_query"."""

        # Get classification from OpenAI
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": "You are a helpful message classification assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=20
        )
        
        # Get intent from response
        intent = response.choices[0].message.content.strip().lower()
        
        # Validate intent
        if intent not in list(intents.keys()) + ["general_query"]:
            return "general_query"
            
        return intent
