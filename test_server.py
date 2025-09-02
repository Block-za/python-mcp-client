#!/usr/bin/env python3
"""
Simple test script to check if the MCP server is running and accessible
"""

import subprocess
import sys
import os

def test_mcp_server():
    """Test if the MCP server is running"""
    server_path = "../build/index.js"
    
    if not os.path.exists(server_path):
        print(f"❌ MCP server not found at {server_path}")
        print("Please build the server first: cd .. && npm run build")
        return False
    
    print(f"✅ MCP server found at {server_path}")
    
    # Try to run the server and see if it starts
    try:
        print("🔄 Testing MCP server startup...")
        process = subprocess.Popen(
            ["node", server_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a few seconds to see if it starts
        import time
        time.sleep(3)
        
        if process.poll() is None:
            print("✅ MCP server started successfully")
            process.terminate()
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"❌ MCP server failed to start")
            print(f"Error: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing MCP server: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing MCP Server Status...")
    print("=" * 50)
    
    if test_mcp_server():
        print("\n✅ MCP server is ready!")
        print("You can now start the client with: python start.py")
    else:
        print("\n❌ MCP server is not ready")
        print("Please fix the issues above before starting the client")
        sys.exit(1)
