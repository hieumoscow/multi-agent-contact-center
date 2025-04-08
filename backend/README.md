# Multi-Customer Contact Center Backend

This is the backend service for the Multi-Customer Contact Center, handling customer interactions, policy queries, and human agent escalations.

## Architecture

### Core Components

#### Agents
- `agents/core/` - Core agent functionality and shared types
  - `base_agent.py` - Base agent class with common functionality
  - `agent_types.py` - Agent type enums and shared data structures
  - `message_classifier.py` - Message intent classification using Azure OpenAI
  - `intents.py` - Intent definitions and constants

- `agents/` - Specialized agents
  - `customer_agent.py` - Handles initial customer interactions and routing
  - `policy_agent.py` - Handles policy-related queries
  - `human_agent.py` - Manages escalations to human agents
  - `agent_manager.py` - Orchestrates agent interactions and conversation state

#### Managers
- `managers/` - Core service managers
  - `chat_manager.py` - Manages Azure Communication Services chat threads
  - `customer_manager.py` - Handles customer data and operations
  - `policy_manager.py` - Manages insurance policy data and queries
  - `escalation_manager.py` - Handles escalation lifecycle and state

### API Endpoints

- `/webhook` - Handles incoming WhatsApp messages
- `/contact-center/chat` - Handles messages from human agents
- `/contact-center/disconnect` - Handles chat disconnection requests

## Dependencies

- Azure OpenAI - For message classification and intent detection
- Azure Communication Services - For chat thread management
- FastAPI - Web framework for API endpoints
- Pydantic - Data validation and settings management

## Environment Variables

Required environment variables:
- `AZURE_OPENAI_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint URL
- `AZURE_OPENAI_DEPLOYMENT` - Azure OpenAI model deployment name
- `AZURE_OPENAI_API_VERSION` - Azure OpenAI API version
- `CHAT_COMMUNICATION_SERVICES_CONNECTION_STRING` - Azure Communication Services connection string
- `CHAT_COMMUNICATION_SERVICES_IDENTITY` - Azure Communication Services identity

## Setup and Running

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables in `.env` file

3. Run the server:
```bash
python api.py
```

## API Endpoints

- `POST /chat`: Send a message to the contact center
  ```json
  {
    "user_id": "string",
    "message": "string"
  }
```

## Development

### Code Organization

The codebase follows a modular architecture:
- Core agent functionality is in `agents/core/`
- Specialized agents in `agents/`
- Service managers in `managers/`
- API endpoints in `api.py`

### Adding New Features

1. For new agent capabilities:
   - Add new intents in `agents/core/intents.py`
   - Update message classifier in `agents/core/message_classifier.py`
   - Implement handling in appropriate agent class

2. For new chat features:
   - Add methods to `managers/chat_manager.py`
   - Update escalation handling in `managers/escalation_manager.py`

3. For new API endpoints:
   - Add routes to `api.py`
   - Update relevant managers and agents

