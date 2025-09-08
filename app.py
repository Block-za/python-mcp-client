import asyncio
import json
import os
import threading
from flask import Flask, render_template, request, jsonify, session, Response
from flask_cors import CORS
# from mcp_client import MCPClient  # Not needed for production
from mcp_http_client import HTTPMCPClient
from database import init_database, db, get_conversations_by_email, create_conversation, get_conversation_by_id, add_message, get_messages_for_context, get_all_messages_for_conversation, should_summarize_conversation, create_conversation_summary, delete_conversation
from summarizer import ConversationSummarizer

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Initialize database
init_database(app)

# Global MCP client instance and event loop
mcp_client = None
event_loop = None
loop_lock = threading.Lock()
summarizer = ConversationSummarizer()

# Check if we're in production mode
IS_PRODUCTION = os.getenv('FLASK_ENV') == 'production'
MCP_SERVER_URL = os.getenv('MCP_SERVER_URL')

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
    
    try:
        if MCP_SERVER_URL:
            # Use HTTP client for both production and testing
            mcp_client = HTTPMCPClient()
            success = await mcp_client.connect_to_server()
            if success:
                print(f"✅ Auto-connected to MCP server at {MCP_SERVER_URL}")
                return True
            else:
                print(f"❌ Failed to auto-connect to MCP server at {MCP_SERVER_URL}")
                return False
        else:
            print("⚠️ No MCP server URL configured for auto-connection")
            return False
    except Exception as e:
        print(f"❌ Auto-connection error: {e}")
        return False

# Auto-connect on startup
def initialize_mcp_connection():
    """Initialize MCP connection on app startup"""
    if MCP_SERVER_URL:
        loop = get_or_create_loop()
        try:
            loop.run_until_complete(auto_connect_mcp_server())
        except Exception as e:
            print(f"Failed to initialize MCP connection: {e}")

# Initialize on import
initialize_mcp_connection()

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/mcp')
def mcp_interface():
    """MCP interface with database chat functionality"""
    return render_template('chat.html')

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

@app.route('/api/query/stream', methods=['POST', 'OPTIONS'])
def process_query_stream():
    """Process a query with streaming response for the simple MCP interface"""
    # Handle preflight requests
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    global mcp_client
    
    if not mcp_client:
        return jsonify({'error': 'Not connected to MCP server'}), 400
    
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        def generate_stream():
            """Generator function for streaming response"""
            try:
                loop = get_or_create_loop()
                
                # Create the streaming coroutine
                async def stream_response():
                    async for chunk in mcp_client.process_query_with_context_stream([{
                        'role': 'user',
                        'content': query
                    }]):
                        yield chunk
                
                # Run the async generator in the loop
                async_gen = stream_response()
                
                try:
                    while True:
                        try:
                            chunk = loop.run_until_complete(async_gen.__anext__())
                            # Ensure chunk is a string and not None
                            if chunk is not None:
                                chunk_str = str(chunk)
                                yield f"data: {json.dumps({'type': 'content', 'content': chunk_str})}\n\n"
                        except StopAsyncIteration:
                            break
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
                
                yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
        return Response(generate_stream(), mimetype='text/event-stream',
                       headers={
                           'Cache-Control': 'no-cache', 
                           'Connection': 'keep-alive',
                           'Access-Control-Allow-Origin': '*',
                           'Access-Control-Allow-Methods': 'POST',
                           'Access-Control-Allow-Headers': 'Content-Type'
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

# Chat Application API Routes

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login with email (simple session-based auth)"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Simple email validation
        if '@' not in email:
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Set session
        session['email'] = email
        
        return jsonify({
            'success': True,
            'email': email,
            'message': 'Logged in successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.pop('email', None)
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    """Check if user is logged in"""
    email = session.get('email')
    return jsonify({
        'logged_in': email is not None,
        'email': email
    })

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get all conversations for the logged-in user"""
    email = session.get('email')
    if not email:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        conversations = get_conversations_by_email(email)
        return jsonify({
            'success': True,
            'conversations': [conv.to_dict() for conv in conversations]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations', methods=['POST'])
def create_new_conversation():
    """Create a new conversation"""
    email = session.get('email')
    if not email:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        title = data.get('title', 'New Conversation')
        
        conversation = create_conversation(email, title)
        
        return jsonify({
            'success': True,
            'conversation': conversation.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<int:conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get a specific conversation and its messages"""
    email = session.get('email')
    if not email:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        conversation = get_conversation_by_id(conversation_id, email)
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        messages = get_all_messages_for_conversation(conversation_id)
        
        return jsonify({
            'success': True,
            'conversation': conversation.to_dict(),
            'messages': [msg.to_dict() for msg in messages]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<int:conversation_id>/messages', methods=['POST'])
def send_message(conversation_id):
    """Send a message in a conversation"""
    email = session.get('email')
    if not email:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        message_content = data.get('content')
        
        if not message_content:
            return jsonify({'error': 'Message content is required'}), 400
        
        # Verify conversation belongs to user
        conversation = get_conversation_by_id(conversation_id, email)
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Add user message
        user_message = add_message(conversation_id, 'user', message_content)
        
        # Update conversation title based on conversation progress
        message_count = len(conversation.messages)
        should_update_title = False
        
        if message_count == 1:  # First message - always update title
            should_update_title = True
        elif message_count == 3:  # After first exchange (user + assistant + user)
            should_update_title = True
        elif message_count % 10 == 1:  # Every 10 messages, refresh the title
            should_update_title = True
        
        if should_update_title:
            # Get all messages for context-aware title generation
            all_messages = get_all_messages_for_conversation(conversation_id)
            messages_dict = [msg.to_dict() for msg in all_messages]
            title = summarizer.generate_conversation_title(messages=messages_dict)
            conversation.title = title
            db.session.commit()
        
        # Get context for AI response (including summaries)
        import database
        context_messages = summarizer.build_context_with_summary(conversation_id, database)
        
        # Prepare messages for MCP client
        mcp_messages = []
        for msg in context_messages:
            mcp_messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
        
        # Add current user message
        mcp_messages.append({
            'role': 'user',
            'content': message_content
        })
        
        # Process with MCP client if available
        assistant_response = "I'm sorry, I'm not connected to an AI service right now. Please connect to an MCP server first."
        
        if mcp_client:
            try:
                # Use the MCP client to process the message
                loop = get_or_create_loop()
                assistant_response = loop.run_until_complete(
                    mcp_client.process_query_with_context(mcp_messages)
                )
            except Exception as e:
                assistant_response = f"Error processing message: {str(e)}"
        
        # Add assistant response
        assistant_message = add_message(conversation_id, 'assistant', assistant_response)
        
        return jsonify({
            'success': True,
            'user_message': user_message.to_dict(),
            'assistant_message': assistant_message.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<int:conversation_id>/messages/stream', methods=['POST', 'OPTIONS'])
def send_message_stream(conversation_id):
    """Send a message in a conversation with streaming response"""
    # Handle preflight requests
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    email = session.get('email')
    if not email:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        data = request.get_json()
        message_content = data.get('content')
        
        if not message_content:
            return jsonify({'error': 'Message content is required'}), 400
        
        # Verify conversation belongs to user
        conversation = get_conversation_by_id(conversation_id, email)
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Add user message
        user_message = add_message(conversation_id, 'user', message_content)
        
        # Update conversation title based on conversation progress
        message_count = len(conversation.messages)
        should_update_title = False
        
        if message_count == 1:  # First message - always update title
            should_update_title = True
        elif message_count == 3:  # After first exchange (user + assistant + user)
            should_update_title = True
        elif message_count % 10 == 1:  # Every 10 messages, refresh the title
            should_update_title = True
        
        if should_update_title:
            # Get all messages for context-aware title generation
            all_messages = get_all_messages_for_conversation(conversation_id)
            messages_dict = [msg.to_dict() for msg in all_messages]
            title = summarizer.generate_conversation_title(messages=messages_dict)
            conversation.title = title
            db.session.commit()
        
        # Get context for AI response (including summaries)
        import database
        context_messages = summarizer.build_context_with_summary(conversation_id, database)
        
        # Prepare messages for MCP client
        mcp_messages = []
        for msg in context_messages:
            mcp_messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
        
        # Add current user message
        mcp_messages.append({
            'role': 'user',
            'content': message_content
        })
        
        def generate_stream():
            """Generator function for streaming response"""
            if not mcp_client:
                yield f"data: {json.dumps({'type': 'error', 'error': 'Not connected to MCP server'})}\n\n"
                return
            
            try:
                print('[API][stream] Starting streaming handler for conversation', conversation_id)
                # Send user message first
                with app.app_context():
                    yield f"data: {json.dumps({'type': 'user_message', 'message': user_message.to_dict()})}\n\n"
                
                # Send typing indicator
                yield f"data: {json.dumps({'type': 'typing', 'status': 'start'})}\n\n"
                
                # Start streaming the assistant response
                assistant_content = ""
                loop = get_or_create_loop()
                
                # Create the streaming coroutine
                async def stream_response():
                    try:
                        async for chunk in mcp_client.process_query_with_context_stream(mcp_messages):
                            # Yield chunks directly; aggregation happens in the outer loop
                            # Debug log server-side to trace content
                            try:
                                sys.stdout.write('[API][stream] chunk len=' + str(len(str(chunk))) + '\n')
                                sys.stdout.flush()
                            except Exception:
                                pass
                            yield chunk
                    except Exception as e:
                        yield f"Error in MCP client streaming: {str(e)}"
                
                # Run the async generator in the loop
                async_gen = stream_response()
                
                try:
                    while True:
                        try:
                            chunk = loop.run_until_complete(async_gen.__anext__())
                            # Ensure chunk is a string and not None
                            if chunk is not None:
                                chunk_str = str(chunk)
                                # Append to assistant_content here only once
                                assistant_content += chunk_str
                                yield f"data: {json.dumps({'type': 'content', 'content': chunk_str})}\n\n"
                        except StopAsyncIteration:
                            break
                        except GeneratorExit:
                            # Handle generator cleanup properly
                            break
                        except Exception as chunk_error:
                            yield f"data: {json.dumps({'type': 'error', 'error': f'Chunk processing error: {str(chunk_error)}'})}\n\n"
                            break
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
                    assistant_content = f"Error processing message: {str(e)}"
                finally:
                    # Ensure the async generator is properly closed
                    try:
                        loop.run_until_complete(async_gen.aclose())
                    except:
                        pass
                
                # Save the complete assistant response to database within app context
                try:
                    with app.app_context():
                        assistant_message = add_message(conversation_id, 'assistant', assistant_content)
                        
                        # Send completion signal with saved message
                        yield f"data: {json.dumps({'type': 'assistant_message', 'message': assistant_message.to_dict()})}\n\n"
                        yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                except Exception as db_error:
                    yield f"data: {json.dumps({'type': 'error', 'error': f'Database error: {str(db_error)}'})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
        return Response(generate_stream(), mimetype='text/event-stream',
                       headers={
                           'Cache-Control': 'no-cache', 
                           'Connection': 'keep-alive',
                           'Access-Control-Allow-Origin': '*',
                           'Access-Control-Allow-Methods': 'POST',
                           'Access-Control-Allow-Headers': 'Content-Type'
                       })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<int:conversation_id>/context', methods=['GET'])
def get_conversation_context(conversation_id):
    """Get context messages for a conversation (for AI processing)"""
    email = session.get('email')
    if not email:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        # Verify conversation belongs to user
        conversation = get_conversation_by_id(conversation_id, email)
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Get context messages (summary + recent messages)
        context_messages = get_messages_for_context(conversation_id)
        
        return jsonify({
            'success': True,
            'context_messages': [msg.to_dict() for msg in context_messages]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<int:conversation_id>', methods=['DELETE'])
def delete_conversation_endpoint(conversation_id):
    """Delete a conversation and all its messages"""
    email = session.get('email')
    if not email:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        # Delete the conversation (with email verification for security)
        success, message = delete_conversation(conversation_id, email)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({'error': message}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<int:conversation_id>/regenerate-title', methods=['POST'])
def regenerate_conversation_title(conversation_id):
    """Regenerate the title for an existing conversation"""
    email = session.get('email')
    if not email:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        # Verify conversation belongs to user
        conversation = get_conversation_by_id(conversation_id, email)
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Get all messages for context-aware title generation
        all_messages = get_all_messages_for_conversation(conversation_id)
        if not all_messages:
            return jsonify({'error': 'No messages found in conversation'}), 400
        
        messages_dict = [msg.to_dict() for msg in all_messages]
        new_title = summarizer.generate_conversation_title(messages=messages_dict)
        
        # Update the conversation title
        conversation.title = new_title
        db.session.commit()
        
        return jsonify({
            'success': True,
            'new_title': new_title,
            'conversation': conversation.to_dict()
        })
        
    except Exception as e:
        print(f"Error regenerating conversation title: {e}")
        return jsonify({'error': 'Failed to regenerate title'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
