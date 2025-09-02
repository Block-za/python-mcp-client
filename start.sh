#!/bin/bash

echo "Starting MCP Client..."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found"
    echo "Please create a .env file with your OpenAI API key:"
    echo "OPENAI_API_KEY=your_api_key_here"
    exit 1
fi

# Install dependencies if needed
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Start the application
echo "Starting Flask application..."
echo "Open your browser to: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo
python3 start.py
