# LinkedIn Messenger

A web application for managing LinkedIn conversations and messages, with real-time notifications.

## Features

- LinkedIn OAuth integration
- View and manage conversations
- Real-time message notifications
- User-friendly interface inspired by modern messaging platforms

## Technologies

- Python 3.9+
- Flask web framework
- Socket.IO for real-time communication
- LinkedIn API integration
- Docker for containerization

## Setup and Installation

### Prerequisites

- Docker and Docker Compose
- LinkedIn Developer Account with API credentials

### Configuration

1. Clone this repository:
   ```
   git clone https://github.com/tenuss2012/linkedin-messenger.git
   cd linkedin-messenger
   ```

2. Copy the example environment file and fill in your LinkedIn API credentials:
   ```
   cp .env.example .env
   ```

3. Update the `.env` file with your LinkedIn OAuth credentials:
   ```
   LINKEDIN_CLIENT_ID=your-client-id
   LINKEDIN_CLIENT_SECRET=your-client-secret
   LINKEDIN_REDIRECT_URI=linkedin.terrynuss.com
   ```

### Running with Docker

1. Build and start the containers:
   ```
   docker-compose up -d
   ```

2. Access the application at `http://localhost:8444`

## Development

### Local Environment Setup

1. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   flask run --port=8444
   ```

## License

Copyright (c) 2025 voov software
