# MCP Client - Blockza Directory Chatbot

A simple web-based chatbot interface for interacting with the Blockza Directory MCP server. This client provides a user-friendly way to query information about companies and events from the Blockza ecosystem.

## Features

- 🤖 **AI-Powered Chatbot**: Uses OpenAI's GPT models to understand and respond to natural language queries
- 🔗 **MCP Server Integration**: Connects to your Blockza Directory MCP server
- 💬 **Real-time Chat Interface**: Modern, responsive web UI for seamless interaction
- 🛠️ **Tool Discovery**: Automatically displays available tools from the MCP server
- 📱 **Mobile Responsive**: Works on desktop and mobile devices
- 🔄 **Conversation History**: Maintains chat history during the session

## Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Node.js (for running the MCP server)
- Blockza Directory MCP server (already set up in parent directory)

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the `mcp-client` directory:

```bash
# Copy the example file
cp env_example.txt .env
```

Edit the `.env` file and add your OpenAI API key:

```
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Build the MCP Server

Make sure the MCP server is built and ready to run:

```bash
# From the parent directory
npm run build
```

## Usage

### Starting the Client

1. Navigate to the mcp-client directory:
```bash
cd mcp-client
```

2. Start the Flask application:
```bash
python app.py
```

3. Open your web browser and go to:
```
http://localhost:5000
```

### Connecting to the Server

1. The application will automatically try to connect to the MCP server at `../build/index.js`
2. If the path is different, update the server path in the connection panel
3. Click "Connect" to establish the connection
4. Once connected, you'll see the available tools listed

### Example Queries

Here are some example queries you can try:

**Company Queries:**
- "Search for crypto companies"
- "Show me companies in the AI category"
- "Get details about a specific company"
- "Find verified companies"
- "Show me companies with affiliate programs"

**Event Queries:**
- "Show me upcoming events"
- "Search for events in New York"
- "Find blockchain conferences"
- "Show events by category"
- "Get event details"

**Analysis Queries:**
- "Compare companies in the DeFi category"
- "Analyze a specific company"
- "Get directory statistics"
- "Show me team members for a company"

## API Endpoints

The client provides the following REST API endpoints:

- `POST /api/connect` - Connect to MCP server
- `POST /api/query` - Send a query to the chatbot
- `GET /api/tools` - Get available tools
- `GET /api/history` - Get conversation history
- `POST /api/clear` - Clear conversation history
- `POST /api/disconnect` - Disconnect from server

## Available Tools

The MCP server provides the following tools:

### Company Tools
- `search_companies` - Search companies by name, category, or criteria
- `get_company_details` - Get detailed information about a specific company
- `get_companies_by_category` - Get all companies in a specific category
- `get_team_members` - Get team member information for a company
- `get_directory_stats` - Get overall directory statistics

### Event Tools
- `search_events` - Search events by title, category, location
- `get_event_details` - Get detailed information about a specific event
- `get_events_by_category` - Get all events in a specific category
- `get_upcoming_events` - Get all upcoming events
- `get_events_by_location` - Get events in a specific location
- `get_events_stats` - Get overall events statistics

### Analysis Tools
- `analyze_company` - Generate comprehensive company analysis
- `compare_companies` - Compare companies in the same category
- `analyze_event` - Generate comprehensive event analysis
- `compare_events` - Compare events in the same category/location
- `event_recommendations` - Get personalized event recommendations

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Ensure the MCP server is built (`npm run build`)
   - Check the server path is correct
   - Verify Node.js is installed and accessible

2. **OpenAI API Errors**
   - Check your API key is correct in the `.env` file
   - Ensure you have sufficient API credits
   - Verify the API key has access to GPT-4o-mini

3. **Tool Execution Errors**
   - The LLM will respond with "I don't have access to the information" if data is not available
   - Check the MCP server logs for any API errors
   - Verify the Blockza API endpoints are accessible

### Error Messages

- **"Not connected to server"**: Click Connect and ensure the server path is correct
- **"Failed to process query"**: Check the server logs and API connectivity
- **"Tool execution failed"**: The MCP server may have encountered an error

## Development

### Project Structure

```
mcp-client/
├── app.py              # Flask web application
├── mcp_client.py       # MCP client implementation
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Web UI template
├── .env               # Environment variables
└── README.md          # This file
```

### Adding New Features

1. **New API Endpoints**: Add routes in `app.py`
2. **UI Enhancements**: Modify `templates/index.html`
3. **Client Logic**: Update `mcp_client.py`

### Testing

The application includes basic error handling and validation. For production use, consider adding:

- Input validation
- Rate limiting
- Authentication
- Logging
- Unit tests

## License

This project is part of the Blockza Directory MCP server implementation.

## Support

For issues related to:
- MCP Client: Check this README and the code comments
- MCP Server: Refer to the parent directory documentation
- Blockza API: Contact the Blockza team
