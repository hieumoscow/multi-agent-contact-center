from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from main import MessagesQuickstart
from managers.chat_manager import ChatThreadManager
from managers.escalation_manager import EscalationManager
from agents import AgentManager
from agents.core.agent_types import ConversationState, Message, AgentType
from dotenv import load_dotenv
import json
import os

# Load environment variables
load_dotenv()

app = FastAPI()
messages = MessagesQuickstart()
chat_manager = ChatThreadManager()
escalation_manager = EscalationManager(chat_manager)
agent = AgentManager()

@app.post("/webhook")
async def webhook(request: Request):
    try:
        # Get JSON body
        try:
            body = await request.json()
            # print("\n WhatsApp Event Grid Request Body:", body)
        except Exception as e:
            # If JSON parsing fails, get raw body
            body = await request.body()
            try:
                # Try to decode as string if possible
                body = body.decode()
            except:
                # If decoding fails, convert bytes to string representation
                body = str(body)
            print("\nRaw Body:", body)
        
        # Handle Event Grid subscription validation
        if isinstance(body, list) and len(body) > 0:
            event = body[0]
            if event.get('eventType') == 'Microsoft.EventGrid.SubscriptionValidationEvent':
                validation_code = event['data']['validationCode']
                print(f"\nValidation Event - Code: {validation_code}")
                return JSONResponse(
                    content={
                        "validationResponse": validation_code
                    },
                    status_code=200
                )
            
            # Handle WhatsApp message events
            if event.get('eventType') == 'Microsoft.Communication.AdvancedMessageReceived':
                print("\n WhatsApp Received Message Event:", body)
                data = event.get('data', {})
                print("\n=== Message Data ===")
                print(f"Event Type: {event.get('eventType')}")
                print(f"Message Type: {data.get('messageType')}")
                print(f"From: {data.get('from')}")
                print(f"Content: {data.get('content')}")
                print(f"Raw Data: {data}")
                
                message_type = data.get('messageType')
                from_number = data.get('from')
                channel_type = data.get('channelType')
                print(f"\nProcessing message from: {from_number}")
                
                # Skip processing if this is a message from our app
                whatsapp_channel_id = os.getenv("WHATSAPP_CHANNEL_ID")
                if not whatsapp_channel_id:
                    raise ValueError("WHATSAPP_CHANNEL_ID not set")
                    
                if from_number == whatsapp_channel_id and channel_type == 'whatsapp':
                    print("Skipping WhatsApp messages from our app")
                    return JSONResponse(
                        content={"status": "Skipped outgoing message"},
                        status_code=200
                    )
                
                if message_type == 'text':
                    # Handle text message
                    content = data.get('content')
                    print(f"Received text message from {from_number}: {content}")
                    
                    # Skip processing if this is a forwarded message from Contact Center
                    if content.startswith("[Contact Center Agent]"):
                        print("Skipping forwarded Contact Center message")
                        return JSONResponse(
                            content={"status": "Skipped forwarded message"},
                            status_code=200
                        )
                    
                    # Process message with Agent
                    ai_response = agent.process_message(from_number, content)
                    
                    # Send AI response
                    if ai_response:
                        # Format response with agent prefix
                        agent_type = agent.conversations[from_number].current_agent
                        if agent_type == AgentType.CUSTOMER_AGENT:
                            prefix = "[Customer Service]"
                        elif agent_type == AgentType.POLICY_AGENT:
                            prefix = "[Policy Agent]"
                        elif agent_type == AgentType.CONTACT_CENTER:
                            prefix = "[Contact Center Agent]"
                        elif agent_type == AgentType.RELATIONSHIP_MANAGER:
                            prefix = "[Relationship Manager]"
                        else:
                            prefix = "[AI Assistant]"
                        
                        formatted_response = f"{prefix} {ai_response}"
                        messages.send_text_message_to(from_number, formatted_response)
                    
                elif message_type in ['image', 'video', 'audio', 'document']:
                    # Handle media message
                    media = data.get('media', {})
                    media_id = media.get('id')
                    mime_type = media.get('mimeType')
                    
                    if media_id and mime_type:
                        print(f"Received {message_type} from {from_number}")
                        # Download and save the media
                        filepath = await messages.download_media(media_id, mime_type)
                        if filepath:
                            print(f"Media saved to: {filepath}")
                            
                            # Process media with Agent
                            ai_response = agent.process_media(from_number, message_type, filepath)
                            
                            # Send AI response
                            if ai_response:
                                messages.send_text_message_to(from_number, ai_response)
                        else:
                            print("Failed to save media")
                            error_message = f"Sorry, there was an issue processing your {message_type}."
                            messages.send_text_message_to(from_number, error_message)
                    
        return JSONResponse(
            content={"status": "success"},
            status_code=200
        )
                    
    except Exception as e:
        # print error and stacktrace
        traceback.print_exc()
        print(f"Error processing webhook: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"message": f"Error processing message: {str(e)}"}
        )

@app.post("/contact-center/chat")
async def chat(request: Request):
    try:
        # Get JSON body
        body = await request.json()
        print("\nContact Center Chat Request Body:", body)

        
        # Validate message type
        if body.get("type") != "Microsoft.Communication.ChatMessageReceived":
            # Handle Event Grid subscription validation
            if isinstance(body, list) and len(body) > 0:
                event = body[0]
                if event.get('eventType') == 'Microsoft.EventGrid.SubscriptionValidationEvent':
                    validation_code = event['data']['validationCode']
                    print(f"\nValidation Event - Code: {validation_code}")
                    return JSONResponse(
                        content={
                            "validationResponse": validation_code
                        },
                        status_code=200
                    )
        
            print(f"Invalid message type: {body.get('type')}")
            return JSONResponse(
                content={"error": "Invalid message type"},
                status_code=400
            )
        
        # Extract message data
        data = body.get("data", {})
        message_body = data.get('messageBody', '')
        sender_name = data.get('senderDisplayName', 'Agent')
        sender_id = data.get('senderId', '')
        
        # Skip if message is from our bot
        fixed_identity = os.getenv("CHAT_COMMUNICATION_SERVICES_IDENTITY")
        if not fixed_identity:
            raise ValueError("CHAT_COMMUNICATION_SERVICES_IDENTITY not set")
            
        if sender_id == fixed_identity:
            print("Skipping ACS chat message from our App")
            return JSONResponse(
                content={"status": "Skipped message from bot"},
                status_code=200
            )
            
        # Get thread ID from event
        thread_id = data.get('threadId')
        
        print(f"\nProcessing message:")
        print(f"Thread ID: {thread_id}")
        print(f"Sender: {sender_name}")
        print(f"Message: {message_body}")
        
        if not all([message_body, thread_id]):
            print("Missing required fields:")
            print(f"- Message Body: {'Present' if message_body else 'Missing'}")
            print(f"- Thread ID: {'Present' if thread_id else 'Missing'}")
            return JSONResponse(
                content={"error": "Missing required fields"},
                status_code=400
            )
        
        # Find the escalation record for this thread
        escalation = escalation_manager.get_escalation(thread_id)
        if not escalation:
            print(f"No escalation found for thread: {thread_id}")
            print("Available thread IDs:", list(escalation_manager.escalations.keys()))
            return JSONResponse(
                content={"error": "No escalation found for thread"},
                status_code=404
            )
        
        print(f"Found escalation record for customer: {escalation.customer_name}")
        
        # Clean up sender name - remove any existing prefixes to prevent nesting
        sender_name = sender_name.strip()
        if sender_name.startswith("[") and sender_name.endswith("]"):
            sender_name = sender_name[1:-1].strip()
        if "Contact Center Agent" in sender_name:
            sender_name = "Agent"
        if " - " in sender_name:
            sender_name = sender_name.split(" - ")[-1].strip()
        
        # Handle short or empty names
        if not sender_name or len(sender_name) <= 1:
            sender_name = "Agent"
            
        # Format message with sender name
        formatted_message = f"[Contact Center Agent] {sender_name}: {message_body}"
        
        # Send message to user's WhatsApp
        try:
            # Get customer phone number from escalation record
            customer_id = escalation.customer_id
            print(f"Sending message to customer at {customer_id}")
            
            # Send message to WhatsApp
            messages.send_text_message_to(customer_id, formatted_message)
            print("Message sent successfully")
            
            return JSONResponse(
                content={"status": "Message sent successfully"},
                status_code=200
            )
        except Exception as e:
            print(f"Error sending message: {str(e)}")
            return JSONResponse(
                content={"error": f"Failed to send message: {str(e)}"},
                status_code=500
            )
            
    except Exception as e:
        # print error and stacktrace
        traceback.print_exc()
        print(f"Error processing contact center chat message: {str(e)}")
        return JSONResponse(
            content={"error": f"Failed to process message: {str(e)}"},
            status_code=500
        )

@app.post("/contact-center/disconnect")
async def disconnect(request: Request):
    try:
        # Get JSON body
        body = await request.json()
        thread_id = body.get("threadId")
        
        if not thread_id:
            return JSONResponse(
                content={"error": "Missing threadId"},
                status_code=400
            )
            
        # Get escalation data
        escalation = escalation_manager.get_escalation(thread_id)
        if not escalation:
            return JSONResponse(
                content={"error": f"No escalation found for thread {thread_id}"},
                status_code=404
            )
            
        # Mark thread as disconnected
        escalation_manager.disconnect_thread(thread_id)
        
        return JSONResponse(
            content={"status": "success"},
            status_code=200
        )
        
    except Exception as e:
        print(f"Error in disconnect endpoint: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@app.options("/contact-center/chat")
async def options_handler(request: Request):
    """Handle HTTP OPTIONS requests for /contact-center/chat"""
    return JSONResponse(
        content={"message": "Allowed methods: POST, OPTIONS"},
        headers={
            "Allow": "POST, OPTIONS",
            "WebHook-Allowed-Origin": "*",  # Replace '*' with the specific origin if known
        },
        status_code=200
    )    

@app.get("/")
async def root():
    return {"message": "WhatsApp Integration API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
