#!/usr/bin/env python3
"""
Test script to verify that tool call conversation flow is correct.
This test ensures that "tool" messages only appear after an "assistant" message with tool_calls.
"""

import asyncio
import json
import os
import sys
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_client import MCPClient

def validate_conversation_flow(messages: List[Dict[str, Any]]) -> bool:
    """
    Validate that the conversation flow follows OpenAI API requirements:
    - "tool" messages must only appear after an "assistant" message with tool_calls
    - Every tool_call_id in "tool" messages must match an id from the preceding assistant's tool_calls
    """
    print("Validating conversation flow...")
    
    for i, message in enumerate(messages):
        print(f"Message {i}: {message.get('role')} - {message.get('content', '')[:50]}...")
        
        if message.get('role') == 'tool':
            # Find the preceding assistant message with tool_calls
            preceding_assistant = None
            for j in range(i-1, -1, -1):
                if messages[j].get('role') == 'assistant':
                    preceding_assistant = messages[j]
                    break
            
            if not preceding_assistant:
                print(f"❌ ERROR: Tool message at index {i} has no preceding assistant message")
                return False
            
            if not preceding_assistant.get('tool_calls'):
                print(f"❌ ERROR: Tool message at index {i} follows assistant message without tool_calls")
                return False
            
            # Validate tool_call_id
            tool_call_id = message.get('tool_call_id')
            valid_ids = [tc.get('id') for tc in preceding_assistant.get('tool_calls', [])]
            
            if tool_call_id not in valid_ids:
                print(f"❌ ERROR: Tool message tool_call_id '{tool_call_id}' not found in preceding assistant tool_calls {valid_ids}")
                return False
    
    print("✅ Conversation flow is valid!")
    return True

async def test_tool_call_flow():
    """Test the fixed tool call conversation flow"""
    print("🧪 Testing tool call conversation flow...")
    
    # Create a mock MCP client
    client = MCPClient()
    
    # Mock the session and OpenAI client
    mock_session = AsyncMock()
    mock_openai_client = Mock()
    
    # Mock tool call response
    mock_tool_call = Mock()
    mock_tool_call.id = "call_test_123"
    mock_tool_call.function.name = "test_tool"
    mock_tool_call.function.arguments = '{"param": "value"}'
    
    # Create a proper message object for the assistant response with tool calls
    class MockMessage:
        def __init__(self, content, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls
            self.role = "assistant"
    
    # Mock OpenAI response with tool calls
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = MockMessage("I'll use a tool to help you.", [mock_tool_call])
    
    # Mock final response after tool execution
    mock_final_response = Mock()
    mock_final_response.choices = [Mock()]
    mock_final_response.choices[0].message = MockMessage("Based on the tool results, here's your answer.", None)
    
    # Mock tool execution result
    mock_tool_result = Mock()
    mock_tool_result.content = [Mock()]
    mock_tool_result.content[0].text = "Tool execution successful"
    
    # Set up the mocks
    client.session = mock_session
    client.openai_client = mock_openai_client
    client.available_tools = [{
        "name": "test_tool",
        "description": "A test tool",
        "input_schema": {"type": "object", "properties": {}}
    }]
    
    # Configure mock responses
    mock_openai_client.chat.completions.create.side_effect = [
        mock_response,  # First call with tool_calls
        mock_final_response  # Second call with final response
    ]
    
    # Ensure the mock message objects have the right attributes
    mock_response.choices[0].message.tool_calls = [mock_tool_call]
    mock_final_response.choices[0].message.tool_calls = None
    
    mock_session.call_tool.return_value = mock_tool_result
    
    # Test the conversation flow
    print("Executing process_query...")
    print(f"Initial conversation history length: {len(client.get_conversation_history())}")
    response = await client.process_query("Test query that triggers tool call")
    print(f"Response: {response}")
    print(f"OpenAI create call count: {mock_openai_client.chat.completions.create.call_count}")
    
    # Get the conversation history
    history = client.get_conversation_history()
    print(f"Final conversation history length: {len(history)}")
    print(f"Raw history: {history}")
    
    print(f"Conversation history has {len(history)} messages:")
    for i, msg in enumerate(history):
        role = msg.get('role')
        content = msg.get('content', '')[:50] + ('...' if len(msg.get('content', '')) > 50 else '')
        tool_calls = msg.get('tool_calls')
        tool_call_id = msg.get('tool_call_id')
        
        print(f"  {i}: {role} - {content}")
        if tool_calls:
            print(f"      tool_calls: {len(tool_calls)} calls")
        if tool_call_id:
            print(f"      tool_call_id: {tool_call_id}")
    
    # Validate the conversation flow
    is_valid = validate_conversation_flow(history)
    
    if is_valid:
        print("✅ Test PASSED: Tool call conversation flow is correct!")
        return True
    else:
        print("❌ Test FAILED: Tool call conversation flow is incorrect!")
        return False

async def test_no_tool_calls():
    """Test conversation flow when no tool calls are made"""
    print("\n🧪 Testing conversation flow without tool calls...")
    
    client = MCPClient()
    
    # Mock the session and OpenAI client
    mock_session = AsyncMock()
    mock_openai_client = Mock()
    
    # Create a proper message object for simple response
    class MockMessage:
        def __init__(self, content, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls
            self.role = "assistant"
    
    # Mock OpenAI response without tool calls
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = MockMessage("Here's a direct answer without using tools.", None)
    
    # Set up the mocks
    client.session = mock_session
    client.openai_client = mock_openai_client
    client.available_tools = []
    
    # Configure mock response
    mock_openai_client.chat.completions.create.return_value = mock_response
    
    # Test the conversation flow
    print("Executing process_query...")
    response = await client.process_query("Simple query")
    print(f"Response: {response}")
    
    # Get the conversation history
    history = client.get_conversation_history()
    print(f"Raw history: {history}")
    
    print(f"Conversation history has {len(history)} messages:")
    for i, msg in enumerate(history):
        role = msg.get('role')
        content = msg.get('content', '')[:50] + ('...' if len(msg.get('content', '')) > 50 else '')
        print(f"  {i}: {role} - {content}")
    
    # Should have user message and assistant response, no tool messages
    expected_roles = ['user', 'assistant']
    actual_roles = [msg.get('role') for msg in history]
    
    if actual_roles == expected_roles:
        print("✅ Test PASSED: Simple conversation flow is correct!")
        return True
    else:
        print(f"❌ Test FAILED: Expected {expected_roles}, got {actual_roles}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Running tool call flow tests...")
    print("=" * 60)
    
    try:
        # Test tool call flow
        test1_passed = await test_tool_call_flow()
        
        # Test no tool calls flow
        test2_passed = await test_no_tool_calls()
        
        print("\n" + "=" * 60)
        if test1_passed and test2_passed:
            print("🎉 ALL TESTS PASSED! Tool call conversation flow is working correctly.")
            return True
        else:
            print("❌ SOME TESTS FAILED! Please check the conversation flow implementation.")
            return False
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    # Run the tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)