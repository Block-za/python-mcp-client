#!/usr/bin/env python3
"""
Simple test to verify auto-connection to deployed MCP server works.
This bypasses the database and just tests the MCP connection.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path so we can import our modules
sys.path.append(os.path.dirname(__file__))

from mcp_http_client import HTTPMCPClient

async def test_mcp_connection():
    """Test connection to deployed MCP server"""
    
    mcp_server_url = os.getenv('MCP_SERVER_URL')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    print("🧪 Testing MCP Auto-Connection")
    print("=" * 50)
    print(f"MCP Server URL: {mcp_server_url}")
    print(f"OpenAI API Key: {'✅ Set' if openai_api_key else '❌ Missing'}")
    print()
    
    if not mcp_server_url:
        print("❌ MCP_SERVER_URL not found in environment")
        return False
    
    if not openai_api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return False
    
    try:
        # Test 1: Create HTTP MCP Client
        print("📡 Creating HTTP MCP Client...")
        client = HTTPMCPClient()
        
        # Test 2: Connect to deployed server
        print("🔗 Connecting to deployed MCP server...")
        success = await client.connect_to_server()
        
        if not success:
            print("❌ Failed to connect to MCP server")
            return False
        
        print("✅ Successfully connected to MCP server!")
        print(f"📊 Available tools: {len(client.available_tools)}")
        
        # Test 3: Try a simple query (simulating user input)
        print("\n🤖 Testing AI query with tools...")
        test_messages = [
            {
                "role": "user", 
                "content": "Show me 3 companies from the Web3 category in Blockza directory"
            }
        ]
        
        print("💭 Processing query with streaming...")
        response = ""
        async for chunk in client.process_query_with_context_stream(test_messages):
            if chunk:
                response += str(chunk)
                print(".", end="", flush=True)  # Show progress
        
        print(f"\n\n📝 Response received ({len(response)} characters)")
        print("First 200 characters:", response[:200] + "..." if len(response) > 200 else response)
        
        # Clean up
        await client.cleanup()
        
        print("\n🎉 SUCCESS! Auto-connection works perfectly!")
        print("✅ Users can now directly start chatting without manual MCP setup")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False

if __name__ == "__main__":
    print("Starting MCP Auto-Connection Test...")
    print("This simulates what happens when a user types a query")
    print("without manually connecting to MCP server.\n")
    
    # Run the async test
    success = asyncio.run(test_mcp_connection())
    
    if success:
        print("\n✅ READY FOR DEPLOYMENT!")
        print("Your auto-connection system is working correctly.")
    else:
        print("\n❌ Need to fix issues before deployment.")
    
    sys.exit(0 if success else 1)
