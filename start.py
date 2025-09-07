#!/usr/bin/env python3
"""
Startup script for MCP Client
Checks prerequisites and starts the Flask application
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        ('flask', 'flask'),
        ('flask-cors', 'flask_cors'),
        ('openai', 'openai'),
        ('mcp', 'mcp'),
        ('python-dotenv', 'dotenv')
    ]
    
    missing_packages = []
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Please run: pip install -r requirements.txt")
        return False
    
    print("✅ All required packages are installed")
    return True

def check_env_file():
    """Check if .env file exists and has OpenAI API key"""
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found")
        print("Please create a .env file with your OpenAI API key:")
        print("OPENAI_API_KEY=your_api_key_here")
        return False
    
    with open(env_file, 'r') as f:
        content = f.read()
        if 'OPENAI_API_KEY' not in content or 'your_api_key_here' in content:
            print("❌ Please set your OpenAI API key in the .env file")
            return False
    
    print("✅ .env file configured")
    return True

def check_mcp_server():
    """Check if MCP server exists"""
    server_path = Path('../blockza-directory-mcp-server/build/index.js')
    if not server_path.exists():
        print("❌ MCP server not found at ../blockza-directory-mcp-server/build/index.js")
        print("Please build the MCP server first:")
        print("cd ../blockza-directory-mcp-server && npm run build")
        return False
    
    print("✅ MCP server found")
    return True

def main():
    """Main startup function"""
    print("🚀 Starting MCP Client...")
    print("=" * 50)
    
    # Check prerequisites
    checks = [
        check_python_version(),
        check_dependencies(),
        check_env_file(),
        check_mcp_server()
    ]
    
    if not all(checks):
        print("\n❌ Prerequisites not met. Please fix the issues above.")
        sys.exit(1)
    
    print("\n✅ All checks passed!")
    print("Starting Flask application...")
    print("Open your browser to: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Start the Flask app
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Shutting down MCP Client...")
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()