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
        
        # Structured response templates
        self.response_templates = {
            "companies": {
                "system_prompt": """You are a helpful assistant that provides information about companies from the Blockza directory. When presenting company information, always format your response using the following structure:

For company lists, use this exact format:
COMPANIES_DATA_START
[
  {
    "_id": "company_id",
    "name": "Company Name",
    "category": "Category",
    "shortDescription": "Brief description",
    "logo": "logo_url",
    "banner": "banner_url", 
    "founderName": "Founder Name",
    "verificationStatus": "verified|pending|rejected",
    "url": "website_url",
    "likes": 0,
    "views": 0
  }
]
COMPANIES_DATA_END

Always include the COMPANIES_DATA_START and COMPANIES_DATA_END markers. Provide a brief summary after the data.""",
                
                "detection_patterns": [
                    "search.*compan",
                    "show.*compan",
                    "list.*compan",
                    "find.*compan",
                    "get.*compan",
                    "compan.*categor",
                    "compan.*verif"
                ]
            },
            
            "events": {
                "system_prompt": """You are a helpful assistant that provides information about events from the Blockza events directory. When presenting event information, always format your response using the following structure:

For event lists, use this exact format:
EVENTS_DATA_START
[
  {
    "id": "event_id",
    "title": "Event Title",
    "company": "Organizer Company",
    "category": "Event Category",
    "location": "City, Country",
    "eventStartDate": "2024-01-01T00:00:00Z",
    "eventEndDate": "2024-01-02T00:00:00Z",
    "website": "event_website_url",
    "featuredImage": "image_url"
  }
]
EVENTS_DATA_END

Always include the EVENTS_DATA_START and EVENTS_DATA_END markers. Provide a brief summary after the data.""",
                
                "detection_patterns": [
                    "search.*event",
                    "show.*event",
                    "list.*event",
                    "find.*event",
                    "get.*event",
                    "event.*categor",
                    "event.*location",
                    "upcoming.*event"
                ]
            },
            
            "team_members": {
                "system_prompt": """You are a helpful assistant that provides information about team members from companies in the Blockza directory. When presenting team member information, always format your response using the following structure:

For team member lists, use this exact format:
TEAM_DATA_START
{
  "company": "Company Name",
  "team_members": [
    {
      "name": "Member Name",
      "title": "Job Title",
      "email": "email@company.com",
      "linkedin": "linkedin_url",
      "image": "profile_image_url",
      "status": "active|inactive",
      "followers": 0,
      "responseRate": 0,
      "price": 0,
      "bookingMethods": ["method1", "method2"]
    }
  ]
}
TEAM_DATA_END

Always include the TEAM_DATA_START and TEAM_DATA_END markers. Provide a brief summary after the data.""",
                
                "detection_patterns": [
                    "team.*member",
                    "show.*team",
                    "list.*team",
                    "get.*team",
                    "compan.*team",
                    "founder.*team"
                ]
            }
        }

    def detect_query_intent(self, query: str) -> Optional[str]:
        """Detect the intent of a query to determine which response template to use"""
        import re
        
        query_lower = query.lower()
        
        for intent, template in self.response_templates.items():
            for pattern in template["detection_patterns"]:
                if re.search(pattern, query_lower):
                    return intent
        
        return None

    def get_system_prompt_for_intent(self, intent: str) -> str:
        """Get the system prompt for a specific intent"""
        if intent in self.response_templates:
            return self.response_templates[intent]["system_prompt"]
        return ""

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

        # Detect query intent and get appropriate system prompt
        intent = self.detect_query_intent(query)
        system_prompt = self.get_system_prompt_for_intent(intent) if intent else ""
        
        # Prepare messages with system prompt if available
        messages = []
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add conversation history
        messages.extend(self.conversation_history)
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": query
        })
        
        # Add user message to history for future reference
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
                messages=messages,
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

                # Get final response from OpenAI with system prompt
                final_messages = []
                if system_prompt:
                    final_messages.append({
                        "role": "system",
                        "content": system_prompt
                    })
                final_messages.extend(self.conversation_history)
                
                final_response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=final_messages,
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
