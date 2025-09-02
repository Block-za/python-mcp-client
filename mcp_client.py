import asyncio
import json
import os
import sys
from typing import Optional, Dict, Any, List
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.available_tools = []
        self.conversation_history = []

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server"""
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        self.available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]
        
        print(f"Connected to server with {len(self.available_tools)} tools")
        return self.available_tools

    async def process_query(self, query: str) -> str:
        """Process a query using OpenAI and available tools"""
        if not self.session:
            return "Error: Not connected to MCP server"

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": query
        })

        # Prepare tools for OpenAI
        tools = []
        for tool in self.available_tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            })

        try:
            # Initial OpenAI API call with timeout
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self.conversation_history,
                tools=tools,
                tool_choice="auto",
                max_tokens=1000,
                timeout=30  # 30 second timeout
            )

            response_message = response.choices[0].message
            self.conversation_history.append(response_message)

            # Check if tool calls are needed
            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    # Execute tool call
                    result = await self.session.call_tool(tool_name, tool_args)
                    
                    # Add tool result to conversation
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result.content[0].text if result.content else "No content returned"
                    })

                # Get final response from OpenAI
                final_response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=self.conversation_history,
                    max_tokens=1000,
                    timeout=30  # 30 second timeout
                )

                final_message = final_response.choices[0].message
                self.conversation_history.append(final_message)
                return final_message.content

            return response_message.content

        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(error_msg)
            # Clear conversation history on error to prevent corruption
            self.conversation_history = []
            return error_msg

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        return self.available_tools

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return self.conversation_history

    def clear_conversation_history(self):
        """Clear conversation history"""
        self.conversation_history = []
