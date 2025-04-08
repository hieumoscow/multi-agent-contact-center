import os
import mimetypes
import asyncio
import aiofiles
from dotenv import load_dotenv
from azure.communication.messages import NotificationMessagesClient
from azure.communication.messages.models import (
    TemplateNotificationContent,
    MessageTemplate,
    TextNotificationContent,
    ImageNotificationContent,
    DocumentNotificationContent,
    AudioNotificationContent,
    VideoNotificationContent
)

# Load environment variables from .env file
load_dotenv()

class MessagesQuickstart(object):
    print("Azure Communication Services - Advanced Messages SDK Quickstart using connection string.")
    # Advanced Messages SDK implementations goes in this section.
   
    connection_string = os.getenv("WHATSAPP_COMMUNICATION_SERVICES_CONNECTION_STRING")
    phone_number = os.getenv("RECIPIENT_PHONE_NUMBER")
    channelRegistrationId = os.getenv("WHATSAPP_CHANNEL_ID")

    def send_template_message(self):
        # client creation
        messaging_client = NotificationMessagesClient.from_connection_string(self.connection_string)
        input_template: MessageTemplate = MessageTemplate(
            name="<<TEMPLATE_NAME>>",
            language="<<LANGUAGE>>")
        template_options = TemplateNotificationContent(
            channel_registration_id=self.channelRegistrationId,
            to=[self.phone_number],
            template=input_template
        )

        # calling send() with WhatsApp template details.
        message_responses = messaging_client.send(template_options)
        response = message_responses.receipts[0]
        
        if (response is not None):
            print("WhatsApp Templated Message with message id {} was successfully sent to {}"
            .format(response.message_id, response.to))
        else:
            print("Message failed to send")

    def send_text_message(self):
        # client creation
        messaging_client = NotificationMessagesClient.from_connection_string(self.connection_string)

        text_message_options = TextNotificationContent(
            channel_registration_id=self.channelRegistrationId,
            to=[self.phone_number],
            content="Hello, World!"
        )

        # calling send() with whatsapp text message
        message_responses = messaging_client.send(text_message_options)
        response = message_responses.receipts[0]
        
        if (response is not None):
            print("WhatsApp Text Message with message id {} was successfully sent to {}"
            .format(response.message_id, response.to))
        else:
            print("Message failed to send")

    def send_text_message_to(self, to_number: str, text: str):
        """Send a text message to a specific phone number"""
        # Create NotificationMessagesClient Client
        messaging_client = NotificationMessagesClient.from_connection_string(self.connection_string)

        text_message_options = TextNotificationContent(
            channel_registration_id=self.channelRegistrationId,
            to=[to_number],
            content=text
        )

        # calling send() with whatsapp text message
        message_responses = messaging_client.send(text_message_options)
        response = message_responses.receipts[0]
        
        if (response is not None):
            print(f"WhatsApp Text Message with message id {response.message_id} was successfully sent to {response.to}")
        else:
            print("Message failed to send")

    def send_image_message(self):
        # Create NotificationMessagesClient Client
        messaging_client = NotificationMessagesClient.from_connection_string(self.connection_string)
        input_media_uri: str = "https://aka.ms/acsicon1"
        image_message_options = ImageNotificationContent(
            channel_registration_id=self.channelRegistrationId,
            to=[self.phone_number],
            media_uri=input_media_uri
        )

        # calling send() with whatsapp image message
        message_responses = messaging_client.send(image_message_options)
        response = message_responses.receipts[0]
        
        if (response is not None):
            print("WhatsApp Image Message with message id {} was successfully sent to {}"
            .format(response.message_id, response.to))
        else:
            print("Message failed to send")
    
    def send_document_message(self):
        # Create NotificationMessagesClient Client
        messaging_client = NotificationMessagesClient.from_connection_string(self.connection_string)
        input_media_uri: str = "##DocumentLinkPlaceholder##"
        documents_options = DocumentNotificationContent(
            channel_registration_id=self.channelRegistrationId,
            to=[self.phone_number],
            caption="Hello World via Advanced Messaging SDK.This is document message",
            media_uri=input_media_uri,
            filename="sample.pdf"
        )

        # calling send() with whatsapp document message
        message_responses = messaging_client.send(documents_options)
        response = message_responses.receipts[0]
        
        if (response is not None):
            print("WhatsApp Document Message with message id {} was successfully sent to {}"
            .format(response.message_id, response.to))
        else:
            print("Message failed to send")

    def send_audio_message(self):
        # Create NotificationMessagesClient Client
        messaging_client = NotificationMessagesClient.from_connection_string(self.connection_string)
        input_media_uri: str = "##AudioLinkPlaceholder##"
        audio_options = AudioNotificationContent(
            channel_registration_id=self.channelRegistrationId,
            to=[self.phone_number],
            media_uri=input_media_uri,
        )

        # calling send() with whatsapp audio message
        message_responses = messaging_client.send(audio_options)
        response = message_responses.receipts[0]
        
        if (response is not None):
            print("WhatsApp Audio Message with message id {} was successfully sent to {}"
            .format(response.message_id, response.to))
        else:
            print("Message failed to send")

    def send_video_message(self):
        # Create NotificationMessagesClient Client
        messaging_client = NotificationMessagesClient.from_connection_string(self.connection_string)
        input_media_uri: str = "##VideoLinkPlaceholder##"
        video_options = VideoNotificationContent(
            channel_registration_id=self.channelRegistrationId,
            to=[self.phone_number],
            media_uri=input_media_uri,
            caption="Video caption"
        )

        # calling send() with whatsapp video message
        message_responses = messaging_client.send(video_options)
        response = message_responses.receipts[0]
        
        if (response is not None):
            print("WhatsApp Video Message with message id {} was successfully sent to {}"
            .format(response.message_id, response.to))
        else:
            print("Message failed to send")

    async def download_media(self, media_id: str, mime_type: str):
        # Create media directory if it doesn't exist
        media_dir = os.path.join(os.path.dirname(__file__), 'media')
        if not os.path.exists(media_dir):
            os.makedirs(media_dir)

        # Create NotificationMessagesClient Client
        messaging_client = NotificationMessagesClient.from_connection_string(self.connection_string)
        try:
            # Get media content as bytes iterator
            media_iterator = messaging_client.download_media(media_id)
            
            # Get MIME type from response
            print(mime_type)
            # Determine file extension from MIME type
            extension = mimetypes.guess_extension(mime_type) or ''
            if not extension and '/' in mime_type:
                # Fallback: use the second part of mime type
                extension = '.' + mime_type.split('/')[-1]
            
            # Create filename with proper extension
            filename = f"{media_id}{extension}"
            filepath = os.path.join(media_dir, filename)
            
            # Save the media content to file by consuming the iterator
            async with aiofiles.open(filepath, 'wb') as f:
                for chunk in media_iterator:
                    await f.write(chunk)
            
            print(f"Media saved successfully to: {filepath}")
            return filepath

        except Exception as e:
            print(f"Media download failed: {str(e)}")
            return None
        finally:
            # Clean up the client
            messaging_client.close()

if __name__ == '__main__':
    messages = MessagesQuickstart()
    # messages.send_template_message()
    asyncio.run(messages.download_media("149e3aa1-38ff-49cb-bbca-b93641d14bcc", "image/jpeg"))
    # messages.send_text_message()
    # messages.send_image_message()
    # messages.send_document_message()
    # messages.send_audio_message()
    # messages.send_video_message()