import asyncio
import json
import os
import threading
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from mcp_client import MCPClient

app = Flask(__name__)
CORS(app)

# Global MCP client instance and event loop
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/connect', methods=['POST'])
def connect_server():
    global mcp_client
    
    try:
        data = request.get_json()
        server_path = data.get('server_path')
        
        if not server_path:
            return jsonify({'error': 'Server path is required'}), 400
        
        # Create new MCP client
        mcp_client = MCPClient()
        
        # Connect to server
        loop = get_or_create_loop()
        tools = loop.run_until_complete(mcp_client.connect_to_server(server_path))
        
        return jsonify({
            'success': True,
            'message': f'Connected to server with {len(tools)} tools',
            'tools': tools
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/query', methods=['POST'])
def process_query():
    global mcp_client
    
    if not mcp_client:
        return jsonify({'error': 'Not connected to MCP server'}), 400
    
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Process query with timeout
        loop = get_or_create_loop()
        
        try:
            response = loop.run_until_complete(
                asyncio.wait_for(
                    mcp_client.process_query(query), 
                    timeout=60  # 60 second timeout
                )
            )
        except asyncio.TimeoutError:
            return jsonify({'error': 'Request timed out after 60 seconds. Please try again.'}), 408
        except Exception as e:
            return jsonify({'error': f'Processing error: {str(e)}'}), 500
        
        return jsonify({
            'success': True,
            'response': response
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tools', methods=['GET'])
def get_tools():
    global mcp_client
    
    if not mcp_client:
        return jsonify({'error': 'Not connected to MCP server'}), 400
    
    try:
        loop = get_or_create_loop()
        tools = loop.run_until_complete(mcp_client.get_available_tools())
        
        return jsonify({
            'success': True,
            'tools': tools
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    global mcp_client
    
    if not mcp_client:
        return jsonify({'error': 'Not connected to MCP server'}), 400
    
    try:
        history = mcp_client.get_conversation_history()
        
        return jsonify({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear', methods=['POST'])
def clear_history():
    global mcp_client
    
    if not mcp_client:
        return jsonify({'error': 'Not connected to MCP server'}), 400
    
    try:
        mcp_client.clear_conversation_history()
        
        return jsonify({
            'success': True,
            'message': 'Conversation history cleared'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    global mcp_client
    
    if not mcp_client:
        return jsonify({'error': 'Not connected to MCP server'}), 400
    
    try:
        loop = get_or_create_loop()
        loop.run_until_complete(mcp_client.cleanup())
        mcp_client = None
        
        return jsonify({
            'success': True,
            'message': 'Disconnected from server'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
