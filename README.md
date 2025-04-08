# Multi-Customer Contact Center

A modern contact center solution that integrates WhatsApp messaging capabilities using Azure Communication Services. This project consists of a Next.js frontend and a Python backend, providing a seamless interface for managing customer communications.

## Features

- WhatsApp messaging integration via Azure Communication Services
- Real-time chat functionality
- Customer management dashboard
- Support for multiple communication channels
- Template message support
- File and media sharing capabilities

## Project Structure

```
multi-customer-contact-center/
├── backend/
   ├── main.py         # Azure Communication Services integration
   ├── api.py          # Backend API endpoints
   └── .env           # Environment configuration
```

## Prerequisites

- Python 3.x
- Node.js and npm
- Azure Communication Services account
- WhatsApp Business Account
- Azure subscription

## Environment Variables

Create a `.env` file in the `backend` directory with the following variables:

```
COMMUNICATION_SERVICES_CONNECTION_STRING=your_connection_string_here
RECIPIENT_PHONE_NUMBER=your_phone_number_here
WHATSAPP_CHANNEL_ID=your_whatsapp_channel_id_here
```

In order to chat to this bot, please whitelist your WhatsApp Phone Number by adding it in the 
[Customer Profile Json](./backend/data/customers.json)

## Setup Instructions

1. Backend Setup
   ```bash
   cd backend
   pip install -r requirements.txt
   python3 main.py
   ```

## Technologies Used

### Backend
- Python
- Azure Communication Services
- Azure SDK for Python


## Features

1. **Customer Management**
   - View and manage customer profiles
   - Track customer interactions
   - Access customer history

2. **Communication Channels**
   - WhatsApp integration
   - Template message support
   - Text message capabilities
   - Media sharing support

3. **Contact Center Portal**
   - Please Deploy ACS Web Chat Hero for Live Agent chat portal: https://github.com/Azure-Samples/communication-services-web-chat-hero

## Security

- Environment variables for sensitive data
- Secure communication with Azure services
- Authentication and authorization implementation

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
