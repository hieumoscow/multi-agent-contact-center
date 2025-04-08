from .message_classifier import Intent

# Disconnect related intents
INTENT_DISCONNECT = Intent(
    "wants_disconnect",
    "User wants to end the conversation",
    ["bye", "disconnect", "end chat", "goodbye"]
)

INTENT_CONFIRM_DISCONNECT = Intent(
    "confirms_disconnect",
    "User confirms they want to end chat (after being asked)",
    ["no thanks", "that's all", "no further questions", "no", "I'm good"]
)

# Service related intents
INTENT_NEEDS_AGENT = Intent(
    "needs_agent",
    "User needs human agent for complex/urgent issues",
    ["speak to agent", "urgent assistance", "complaint", "talk to human"]
)

INTENT_NEEDS_RM = Intent(
    "needs_rm",
    "User needs relationship manager for complex financial queries",
    ["portfolio review", "investment strategy", "financial planning"]
)

# Common groups of intents
DISCONNECT_INTENTS = [INTENT_DISCONNECT, INTENT_CONFIRM_DISCONNECT]
ESCALATION_INTENTS = [INTENT_NEEDS_AGENT, INTENT_NEEDS_RM]
