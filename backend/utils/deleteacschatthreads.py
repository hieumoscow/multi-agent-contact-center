import os
from azure.communication.identity import CommunicationIdentityClient
from azure.communication.chat import (
    ChatClient,
    CommunicationTokenCredential,
    ChatMessageType,
    CommunicationUserIdentifier
)
from dotenv import load_dotenv
import time

def delete_all_chat_threads():
    # Load environment variables
    load_dotenv()
    
    # Get Azure credentials from environment
    connection_string = os.getenv("CHAT_COMMUNICATION_SERVICES_CONNECTION_STRING")
    fixed_identity = os.getenv("CHAT_COMMUNICATION_SERVICES_IDENTITY")
    if not connection_string:
        raise ValueError("CHAT_COMMUNICATION_SERVICES_CONNECTION_STRING not set")
    if not fixed_identity:
        raise ValueError("CHAT_COMMUNICATION_SERVICES_IDENTITY not set")
    
    print("\nIdentity ID:", fixed_identity)
    
    # Initialize identity client
    identity_client = CommunicationIdentityClient.from_connection_string(connection_string)
    
    # Get token for fixed identity
    token_response = identity_client.get_token(
        CommunicationUserIdentifier(fixed_identity),
        ["chat"]
    )
    
    print("\nAccess Token:", token_response.token)
    print("\nExpires:", token_response.expires_on)
    
    # Initialize chat client with token
    chat_client = ChatClient(
        endpoint=connection_string.split(';')[0].split('=')[1],
        credential=CommunicationTokenCredential(token_response.token)
    )
    
    # Get all chat threads
    threads = list(chat_client.list_chat_threads())
    total_threads = len(threads)
    deleted_count = 0
    failed_count = 0
    
    print(f"Found {total_threads} chat threads to delete...")
    
    # Delete each thread with rate limiting
    for i, thread in enumerate(threads, 1):
        try:
            chat_client.delete_chat_thread(thread.id)
            deleted_count += 1
            print(f"[{i}/{total_threads}] Deleted thread {thread.id}")
            # Add delay between requests to avoid rate limiting
            time.sleep(1)
        except Exception as e:
            failed_count += 1
            print(f"[{i}/{total_threads}] Failed to delete thread {thread.id}: {str(e)}")
            # If we hit rate limit, wait longer
            if "TooManyRequests" in str(e):
                print("Rate limit hit, waiting 5 seconds...")
                time.sleep(5)
    
    print(f"\nSummary:")
    print(f"Total threads: {total_threads}")
    print(f"Successfully deleted: {deleted_count}")
    print(f"Failed to delete: {failed_count}")

if __name__ == "__main__":
    delete_all_chat_threads()