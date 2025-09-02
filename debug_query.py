#!/usr/bin/env python3
"""
Debug script to test queries and identify where hanging occurs
"""

import asyncio
import os
import sys
from mcp_client import MCPClient
from dotenv import load_dotenv

load_dotenv()

async def debug_query():
    """Debug a query to see where it hangs"""
    print("🔍 Debugging MCP Query...")
    print("=" * 50)
    
    # Check environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in .env file")
        return
    
    print("✅ OpenAI API key found")
    
    # Create client
    print("🔄 Creating MCP client...")
    client = MCPClient()
    
    # Connect to server
    print("🔄 Connecting to MCP server...")
    try:
        tools = await client.connect_to_server("../blockza-directory-mcp-server/build/index.js")
        print(f"✅ Connected with {len(tools)} tools")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return
    
    # Test query
    test_query = "Show me list of categories available"
    print(f"\n🔄 Testing query: '{test_query}'")
    
    try:
        print("🔄 Processing query...")
        response = await asyncio.wait_for(
            client.process_query(test_query),
            timeout=60
        )
        print("✅ Query completed successfully!")
        print(f"Response: {response}")
    except asyncio.TimeoutError:
        print("❌ Query timed out after 60 seconds")
    except Exception as e:
        print(f"❌ Query failed: {e}")
    finally:
        print("🔄 Cleaning up...")
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(debug_query())
