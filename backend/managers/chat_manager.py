import os
from datetime import datetime, timedelta
from azure.communication.identity import CommunicationIdentityClient
from azure.communication.chat import (
    ChatClient,
    CommunicationTokenCredential,
    ChatMessageType,
    CommunicationUserIdentifier
)
from typing import Dict, List, Tuple, Optional

class ChatThreadManager:
    def __init__(self):
        self.connection_string = os.getenv("CHAT_COMMUNICATION_SERVICES_CONNECTION_STRING")
        if not self.connection_string:
            raise ValueError("CHAT_COMMUNICATION_SERVICES_CONNECTION_STRING not found in environment variables")
            
        self.endpoint = self.connection_string.split(';')[0].split('=')[1]
        
        # Initialize the identity client
        self.identity_client = CommunicationIdentityClient.from_connection_string(self.connection_string)
        
        # Use fixed ACS identity from environment variable
        self.fixed_identity = os.getenv("CHAT_COMMUNICATION_SERVICES_IDENTITY")
        if not self.fixed_identity:
            raise ValueError("CHAT_COMMUNICATION_SERVICES_IDENTITY not set")
            
        # Store active chat threads
        self.active_threads = {}  # Format: {phone_number: (thread_id, chat_client, expiry)}

    def _get_chat_token(self):
        """Get chat token for fixed identity"""
        return self.identity_client.get_token(
            CommunicationUserIdentifier(self.fixed_identity),
            ["chat"]
        )

    def get_or_create_thread(self, phone_number: str) -> tuple:
        """Get existing thread or create new one for the phone number
        Returns: (thread_id, chat_client, is_new_thread)"""
        current_time = datetime.now()
        
        # Check if there's an active thread for this phone number
        if phone_number in self.active_threads:
            thread_id, chat_client, expiry = self.active_threads[phone_number]
            if current_time < expiry:
                return thread_id, chat_client, False
                
        # Get token for fixed identity
        token_result = self._get_chat_token()
        
        # Create chat client
        chat_client = ChatClient(
            self.endpoint,
            CommunicationTokenCredential(token_result.token)
        )
        
        print("Creating chat thread for", phone_number, "...")
        # Create new thread
        topic = f"WhatsApp Chat with {phone_number} - {current_time.strftime('%Y-%m-%d')}"
        create_thread_result = chat_client.create_chat_thread(topic)
        thread_id = create_thread_result.chat_thread.id
        
        print("Chat thread created:", thread_id)
        # Store thread info with 24-hour expiry
        expiry = current_time + timedelta(hours=1)
        self.active_threads[phone_number] = (thread_id, chat_client, expiry)
        
        return thread_id, chat_client, True
        
    def add_message_to_thread(self, phone_number: str, content: str, is_from_whatsapp: bool = True):
        """Add a message to the chat thread"""
        thread_id, chat_client, _ = self.get_or_create_thread(phone_number)
        chat_thread_client = chat_client.get_chat_thread_client(thread_id)
        
        # Prepare message details
        sender_name = f"WhatsApp User ({phone_number})" if is_from_whatsapp else "System"
        
        # Send message to thread
        send_result = chat_thread_client.send_message(
            content=content,
            sender_display_name=sender_name,
            chat_message_type=ChatMessageType.TEXT
        )
        return send_result.id
        
    def add_media_message_to_thread(self, phone_number: str, media_type: str, filepath: str, is_from_whatsapp: bool = True):
        """Add a media message to the chat thread"""
        thread_id, chat_client, _ = self.get_or_create_thread(phone_number)
        chat_thread_client = chat_client.get_chat_thread_client(thread_id)
        
        # Prepare message details
        sender_name = f"WhatsApp User ({phone_number})" if is_from_whatsapp else "System"
        content = f"Sent a {media_type}"
        
        # Add metadata for the media file
        metadata = {
            'mediaType': media_type,
            'filePath': filepath
        }
        
        # Send message to thread
        send_result = chat_thread_client.send_message(
            content=content,
            sender_display_name=sender_name,
            chat_message_type=ChatMessageType.TEXT,
            metadata=metadata
        )
        return send_result.id

    def cleanup_chat_thread(self, thread_id: str):
        """Remove participant and delete chat thread on disconnect"""
        try:
            print(f"Cleaning up chat thread {thread_id}")
            # Get token and create chat client
            token_result = self._get_chat_token()
            chat_client = ChatClient(
                self.endpoint,
                CommunicationTokenCredential(token_result.token)
            )
            
            # Get chat thread client
            chat_thread_client = chat_client.get_chat_thread_client(thread_id)
            
            try:
                # Delete the chat thread
                chat_thread_client.delete_chat_thread()
                print(f"Chat thread {thread_id} deleted")
            except Exception as e:
                print(f"Error deleting chat thread: {e}")
                
            # Remove from active threads
            for phone_number, (tid, _, _) in list(self.active_threads.items()):
                if tid == thread_id:
                    del self.active_threads[phone_number]
                    break
                    
        except Exception as e:
            print(f"Error cleaning up chat thread: {e}")
