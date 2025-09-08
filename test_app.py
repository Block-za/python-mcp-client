#!/usr/bin/env python3
"""
Simple Flask app to test MCP auto-connection without database
"""

import asyncio
import json
import os
import threading
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our MCP client
from mcp_http_client import HTTPMCPClient

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('SECRET_KEY', 'test-secret-key')

# Global MCP client
mcp_client = None
event_loop = None
loop_lock = threading.Lock()

def get_or_create_loop():
    """Get the current event loop or create a new one"""
    global event_loop
    with loop_lock:
        if event_loop is None or event_loop.is_closed():
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)
        return event_loop

async def auto_connect_mcp_server():
    """Auto-connect to MCP server on startup"""
    global mcp_client
    
    mcp_server_url = os.getenv('MCP_SERVER_URL')
    if not mcp_server_url:
        print("⚠️ No MCP server URL configured")
        return False
    
    try:
        mcp_client = HTTPMCPClient()
        success = await mcp_client.connect_to_server()
        if success:
            print(f"✅ Auto-connected to MCP server at {mcp_server_url}")
            return True
        else:
            print(f"❌ Failed to auto-connect to MCP server")
            return False
    except Exception as e:
        print(f"❌ Auto-connection error: {e}")
        return False

# Initialize MCP connection
def initialize_mcp_connection():
    """Initialize MCP connection on app startup"""
    loop = get_or_create_loop()
    try:
        loop.run_until_complete(auto_connect_mcp_server())
    except Exception as e:
        print(f"Failed to initialize MCP connection: {e}")

# Auto-connect on startup
initialize_mcp_connection()

@app.route('/')
def index():
    """Simple chat interface"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Blockza AI Test</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .chat-container { border: 1px solid #ddd; height: 400px; overflow-y: scroll; padding: 10px; margin: 10px 0; }
            .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
            .user { background: #e3f2fd; text-align: right; }
            .assistant { background: #f5f5f5; }
            .input-container { display: flex; gap: 10px; }
            input { flex: 1; padding: 10px; }
            button { padding: 10px 20px; }
        </style>
    </head>
    <body>
        <h1>🚀 Blockza AI Chat Test</h1>
        <p><strong>MCP Server Status:</strong> <span id="status">Checking...</span></p>
        
        <div class="chat-container" id="chat"></div>
        
        <div class="input-container">
            <input type="text" id="messageInput" placeholder="Ask about companies in Blockza directory..." 
                   onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Send</button>
        </div>

        <script>
            // Check MCP status on load
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('status').textContent = data.mcp_connected ? '✅ Connected' : '❌ Disconnected';
                });

            function addMessage(content, role) {
                const chat = document.getElementById('chat');
                const div = document.createElement('div');
                div.className = 'message ' + role;
                div.innerHTML = content;
                chat.appendChild(div);
                chat.scrollTop = chat.scrollHeight;
            }

            function sendMessage() {
                const input = document.getElementById('messageInput');
                const message = input.value.trim();
                if (!message) return;

                addMessage(message, 'user');
                input.value = '';

                // Send to backend
                fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message})
                })
                .then(response => response.text())
                .then(data => {
                    addMessage(data || 'No response', 'assistant');
                })
                .catch(error => {
                    addMessage('Error: ' + error, 'assistant');
                });
            }
        </script>
    </body>
    </html>
    '''

@app.route('/api/status')
def status():
    """Check MCP connection status"""
    return jsonify({
        'mcp_connected': mcp_client is not None,
        'mcp_server_url': os.getenv('MCP_SERVER_URL'),
        'tools_available': len(mcp_client.available_tools) if mcp_client else 0
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    """Process chat message"""
    if not mcp_client:
        return "❌ MCP server not connected"
    
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return "Please provide a message"
        
        # Process message with MCP client
        loop = get_or_create_loop()
        
        async def process_message():
            try:
                response = ""
                async for chunk in mcp_client.process_query_with_context_stream([{
                    'role': 'user',
                    'content': message
                }]):
                    if chunk:
                        response += str(chunk)
                
                return response or "No response generated"
                
            except Exception as e:
                return f"Error processing message: {str(e)}"
        
        result = loop.run_until_complete(process_message())
        return result
        
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == '__main__':
    print("🚀 Starting Blockza AI Test Server...")
    print(f"MCP Server: {os.getenv('MCP_SERVER_URL')}")
    print("Visit: http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)
