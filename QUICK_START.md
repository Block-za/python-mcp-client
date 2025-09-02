# Quick Start Guide

## 🚀 Get Started in 3 Steps

### 1. Set up your OpenAI API Key
Create a `.env` file in the `mcp-client` directory:
```
OPENAI_API_KEY=your_actual_openai_api_key_here
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the Client
**Windows:**
```bash
start.bat
```

**Mac/Linux:**
```bash
./start.sh
```

**Manual:**
```bash
python start.py
```

## 🌐 Access the Chatbot
Open your browser and go to: **http://localhost:5000**

## 💬 Try These Example Queries

- "Search for crypto companies"
- "Show me upcoming events"
- "Find companies in the AI category"
- "Get directory statistics"
- "Show me events in New York"

## 🔧 Troubleshooting

**If you get "Connection Failed":**
- Make sure the MCP server is built: `cd ../blockza-directory-mcp-server && npm run build`
- Check the server path is correct (default: `../blockza-directory-mcp-server/build/index.js`)

**If you get "OpenAI API Error":**
- Verify your API key in the `.env` file
- Check you have sufficient API credits

**If tools don't work:**
- The LLM will respond with "I don't have access to the information" if data isn't available
- This is the expected behavior per your requirements

## 📁 Files Created

- `mcp_client.py` - Core MCP client implementation
- `app.py` - Flask web server
- `templates/index.html` - Chatbot UI
- `start.py` - Startup script with checks
- `start.bat` / `start.sh` - Platform-specific launchers
- `requirements.txt` - Python dependencies
- `README.md` - Full documentation

The chatbot is now ready to use! 🎉
