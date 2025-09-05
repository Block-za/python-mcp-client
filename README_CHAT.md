# AI Chat Application

A modern chat application built with Flask, PostgreSQL, and OpenAI integration, featuring conversation management, message summarization, and MCP (Model Context Protocol) support.

## Features

- **User Authentication**: Simple email-based login system
- **Conversation Management**: Create, view, and manage multiple conversations
- **Message Persistence**: All messages stored in PostgreSQL database
- **AI Integration**: OpenAI GPT integration with MCP server support
- **Conversation Summarization**: Automatic summarization of long conversations
- **Modern UI**: Clean, responsive interface similar to ChatGPT
- **Real-time Chat**: Instant message sending and receiving

## Architecture

### Backend (Flask + PostgreSQL)
- **Database Models**: Conversations and Messages with proper relationships
- **API Routes**: RESTful endpoints for authentication, conversations, and messages
- **Summarization Logic**: Intelligent conversation summarization for context management
- **MCP Integration**: Support for Model Context Protocol servers

### Frontend (Vanilla JavaScript)
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Updates**: Dynamic conversation loading and message display
- **Modern UI**: Clean interface with sidebar navigation and chat window

## Database Schema

### Conversations Table
- `id`: Primary key
- `email`: User email (identifier)
- `title`: Conversation title (auto-generated)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Messages Table
- `id`: Primary key
- `conversation_id`: Foreign key to conversations
- `role`: Message role (user, assistant, system)
- `content`: Message content
- `timestamp`: Message timestamp
- `is_summary`: Boolean flag for summary messages

## Installation

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- OpenAI API key

### Setup Steps

1. **Clone and navigate to the project**:
   ```bash
   cd mcp-client
   ```

2. **Run the setup script**:
   ```bash
   python setup.py
   ```

3. **Configure environment variables**:
   ```bash
   # Copy the example file
   cp env_config.txt .env
   
   # Edit .env with your actual values
   OPENAI_API_KEY=your_openai_api_key_here
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=chat_app
   DB_USER=postgres
   DB_PASSWORD=your_password
   SECRET_KEY=your-secret-key-here
   ```

4. **Initialize the database**:
   ```bash
   # The setup script should handle this, but you can also run manually:
   psql -U postgres -d chat_app -f database_schema.sql
   ```

5. **Start the application**:
   ```bash
   python app.py
   ```

6. **Access the application**:
   Open your browser and go to `http://localhost:5000`

## Usage

### Basic Chat Flow

1. **Login**: Enter your email address to log in
2. **Create Conversation**: Click "New Chat" to start a new conversation
3. **Send Messages**: Type your message and press Enter or click Send
4. **View History**: Click on any conversation in the sidebar to view its history
5. **Logout**: Click the logout button to end your session

### Conversation Management

- **Auto-titling**: Conversations are automatically titled based on the first message
- **Message Persistence**: All messages are saved and can be viewed later
- **Summarization**: Long conversations are automatically summarized to maintain context
- **Context Management**: The system maintains conversation context using summaries + recent messages

### MCP Integration

The application supports MCP servers for enhanced AI capabilities:

1. **Connect to MCP Server**: Use the existing MCP connection functionality
2. **Enhanced Responses**: AI responses can use MCP tools for better functionality
3. **Tool Integration**: Supports various MCP tools for different use cases

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login with email
- `POST /api/auth/logout` - Logout user
- `GET /api/auth/status` - Check authentication status

### Conversations
- `GET /api/conversations` - Get all conversations for user
- `POST /api/conversations` - Create new conversation
- `GET /api/conversations/<id>` - Get specific conversation and messages
- `POST /api/conversations/<id>/messages` - Send message in conversation
- `GET /api/conversations/<id>/context` - Get conversation context for AI

### MCP Integration (Existing)
- `POST /api/connect` - Connect to MCP server
- `POST /api/query` - Process query with MCP
- `GET /api/tools` - Get available MCP tools
- `POST /api/disconnect` - Disconnect from MCP server

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for AI responses | Required |
| `DATABASE_URL` | PostgreSQL connection URL | - |
| `DB_HOST` | PostgreSQL host | localhost |
| `DB_PORT` | PostgreSQL port | 5432 |
| `DB_NAME` | Database name | chat_app |
| `DB_USER` | Database user | postgres |
| `DB_PASSWORD` | Database password | password |
| `SECRET_KEY` | Flask secret key | your-secret-key-here |

### Summarization Settings

The summarization logic can be configured in `summarizer.py`:

- `summary_threshold`: Number of messages before summarization (default: 20)
- `context_limit`: Number of recent messages to keep in context (default: 10)

## Development

### Project Structure

```
mcp-client/
├── app.py                 # Main Flask application
├── database.py           # Database models and operations
├── summarizer.py         # Conversation summarization logic
├── mcp_client.py         # MCP client integration
├── database_schema.sql   # PostgreSQL schema
├── setup.py             # Setup script
├── requirements.txt     # Python dependencies
├── env_config.txt       # Environment configuration template
├── templates/
│   ├── index.html       # Original MCP interface
│   └── chat.html        # New chat interface
└── README.md           # This file
```

### Adding New Features

1. **Database Changes**: Update `database_schema.sql` and `database.py`
2. **API Endpoints**: Add new routes in `app.py`
3. **Frontend**: Update `templates/chat.html` for UI changes
4. **MCP Integration**: Extend `mcp_client.py` for new MCP features

### Testing

The application includes basic error handling and validation. For production use, consider adding:

- Unit tests for database operations
- API endpoint testing
- Frontend testing
- Integration tests for MCP functionality

## Troubleshooting

### Common Issues

1. **Database Connection Error**:
   - Ensure PostgreSQL is running
   - Check database credentials in `.env`
   - Verify database exists

2. **OpenAI API Error**:
   - Verify `OPENAI_API_KEY` is set correctly
   - Check API key has sufficient credits
   - Ensure internet connection

3. **MCP Server Connection**:
   - Verify MCP server path is correct
   - Check MCP server is running
   - Review MCP server logs

### Logs

The application logs important events to the console. For production, consider adding proper logging configuration.

## License

This project is part of the MCP (Model Context Protocol) integration and follows the same licensing terms.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Ensure all dependencies are installed correctly
4. Verify environment configuration
