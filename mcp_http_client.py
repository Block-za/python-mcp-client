"""
HTTP-based MCP Client for production deployment.
This client connects to MCP servers over HTTP/SSE instead of stdio.
"""

import asyncio
import json
import os
import sys
import time
import aiohttp
from typing import Optional, Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class HTTPMCPClient:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.available_tools = []
        self.conversation_history = []
        self.mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:3001")
        
        # Enhanced system prompt based on Blockza template
        self.base_system_prompt = """You are a professional AI assistant for Blockza — a Web3 platform offering AI-powered company directories, partner discovery, and meeting booking.

🎯 Your response must be formatted using clean Bootstrap 5-compatible HTML, styled like https://blockza.io.

⚠️ IMPORTANT:
- Your first priority is to directly and professionally answer the user's question in a clear and well structured way using Bootstrap for it.
- Use bullet points, short paragraphs, and emphasize the benefit of using Blockza features such as directory listings, meeting bookings, visibility, or tools.
- After the main response, you may display "Similar Companies of [CATEGORY]".
- When users ask for companies by category (Web3, NFT, Blockchain, AI, DeFi, etc.), ALWAYS use the "get_companies_by_category" tool for the most accurate category-specific results.

✅ Guidelines:
- Use one font-size 16px and one font-family 
- Do NOT show random company profile unless specifically asked.
- Do NOT skip the main answer.
- Do NOT wrap output in code blocks like ```html.
- Avoid repeating "Sorry" or generic statements if confident context exists.
- If a user asks about any specific category — including: Blockchain, Web3, Crypto, DeFi, DAO, Metaverse, NFT, Blockchain Game, or AI — return a list of relevant companies from that category using the Bootstrap 5-compatible HTML format provided below.

For company displays, use this format:
<div class='d-flex align-items-center mb-3'>
  <img src='LOGO_URL' class='me-3' style='width:60px; height:60px; border-radius:50%;'>
  <div>
    <h3 class='mb-1'>Company Name</h3>
    <p class='text-muted mb-0'>Short tagline or summary of the company</p>
  </div>
</div>
<p>Detailed overview of the company's mission, technology, services, and goals.</p>
<div class='mt-3'>
  <a href='[DirectoryLink]' target='_blank' class='btn btn-outline-primary btn-sm me-2'>View Directory</a>
</div>
---

For team member displays, use this format:
<h4><i class="bi bi-people-fill"></i> Team</h4>
<div class='row row-cols-1 row-cols-sm-2 row-cols-md-3 g-4'>
  <div class='col'>
    <div class='card text-center h-100'>
      <img src='IMAGE_URL' class='card-img-top' style='height:150px; object-fit:cover;'>
      <div class='card-body'>
        <h5 class='card-title'>Full Name</h5>
        <p class='text-muted'>Role</p>
        <p>Optional description or quote</p>
        <strong id="BookMeeting_[Name]" data-name="Name" class="btn btn-sm btn-outline-primary m-2 cursor-pointer">Book a Meeting</strong>
      </div>
    </div>
  </div>
</div>

For company listings, use this format:
<h4 class="pt-4"><i class="bi bi-building"></i> Similar Companies of [CATEGORY]</h4>
<div class='row'>
  <div class='col-12 col-sm-6 col-md-4 pb-4'>
    <div class='card h-100 shadow-sm border-0'>
      <img src='BANNER_IMAGE_URL' class='card-img-top' alt='Company Banner'>
      <div class='card-body'>
        <h5 class='card-title mb-1'>Company Name</h5>
        <p class='text-muted small mb-2'>Short company description...</p>
        <a href='[DirectoryLink]' target='_blank' class='btn btn-outline-secondary btn-sm mt-2'>View Directory</a>
      </div>
    </div>
  </div>
</div>

🚫 Do not include personal emails, phone numbers, or LinkedIn.
✅ Promote the "Book a Meeting" button where relevant."""

    def get_system_prompt(self) -> str:
        """Get the enhanced system prompt for all queries"""
        return self.base_system_prompt

    async def connect_to_server(self) -> bool:
        """Connect to an HTTP MCP server and discover tools"""
        try:
            # Create HTTP session
            self.session = aiohttp.ClientSession()
            
            # Check server health
            async with self.session.get(f"{self.mcp_server_url}/health") as response:
                if response.status != 200:
                    raise Exception(f"Server health check failed: {response.status}")
                
                health_data = await response.json()
                print(f"Connected to {health_data.get('server', 'MCP Server')}")
                
                # For now, we'll hardcode the available tools since HTTP MCP doesn't have
                # a standard tool discovery endpoint. In a full implementation, this would
                # be part of the MCP HTTP specification.
                self.available_tools = self._get_blockza_tools()
                
                return True
                
        except Exception as e:
            print(f"Failed to connect to MCP server: {e}")
            if self.session:
                await self.session.close()
                self.session = None
            return False

    def _get_blockza_tools(self) -> List[Dict[str, Any]]:
        """Return the hardcoded list of Blockza tools available on the server"""
        return [
            {
                "name": "search_companies",
                "description": "Search companies in the Blockza directory by name or general search terms",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "search": {"type": "string", "description": "Search term to find companies"},
                        "category": {"type": "string", "description": "Filter by company category"},
                        "limit": {"type": "number", "description": "Maximum number of results"},
                        "verified_only": {"type": "boolean", "description": "Show only verified companies"}
                    }
                }
            },
            {
                "name": "get_company_details",
                "description": "Get detailed information about a specific company by slug or name",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "identifier": {"type": "string", "description": "Company slug or name to look up"},
                        "include_team": {"type": "boolean", "description": "Include team member information"}
                    },
                    "required": ["identifier"]
                }
            },
            {
                "name": "get_companies_by_category",
                "description": "PRIMARY TOOL for retrieving all companies in a specific category",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Category to filter by"},
                        "limit": {"type": "number", "description": "Maximum number of results"}
                    },
                    "required": ["category"]
                }
            },
            # Add more tools as needed...
        ]

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Call a tool on the MCP server via HTTP"""
        if not self.session:
            raise Exception("Not connected to MCP server")
        
        try:
            # For now, we'll make direct API calls to Blockza since we don't have
            # a standardized HTTP MCP tool calling protocol yet.
            # In a full implementation, this would call the MCP server's tool endpoint.
            
            if tool_name == "search_companies":
                return await self._call_blockza_api("directory", args)
            elif tool_name == "get_companies_by_category":
                return await self._call_blockza_api("directory", {"category": args.get("category")})
            elif tool_name == "get_company_details":
                return await self._call_blockza_api("directory", {"search": args.get("identifier")})
            else:
                return f"Tool {tool_name} not implemented in HTTP client"
                
        except Exception as e:
            return f"Error calling tool {tool_name}: {str(e)}"

    async def _call_blockza_api(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Make direct API calls to Blockza (temporary implementation)"""
        base_url = "https://api.blockza.io/api"
        
        try:
            url = f"{base_url}/{endpoint}"
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return json.dumps(data, indent=2)
                else:
                    return f"API error: {response.status}"
        except Exception as e:
            return f"API call failed: {str(e)}"

    async def process_query_with_context_stream(self, context_messages: List[Dict[str, Any]]):
        """Process a query with provided context messages and stream the response"""
        if not self.session:
            yield "Error: Not connected to MCP server"
            return
        
        # Use the enhanced system prompt for all queries
        system_prompt = self.get_system_prompt()
        
        # Prepare messages with system prompt
        messages = [{
            "role": "system",
            "content": system_prompt
        }]
        
        # Add context messages
        messages.extend(context_messages)
        
        async for chunk in self._process_messages_stream(messages):
            yield chunk

    async def _process_messages_stream(self, messages: List[Dict[str, Any]]):
        """Internal method to stream messages with OpenAI and tools"""
        
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
            # Initial OpenAI API call with streaming
            stream = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=1000,
                timeout=30,
                stream=True
            )

            full_response = ""
            tool_calls = []
            current_tool_call = None
            current_tool_index = None
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
                
                # Handle tool calls in streaming (similar to original implementation)
                if chunk.choices[0].delta.tool_calls:
                    for tool_call in chunk.choices[0].delta.tool_calls:
                        idx = tool_call.index
                        name_delta = tool_call.function.name if tool_call.function else None
                        args_delta = tool_call.function.arguments if tool_call.function else None

                        if current_tool_call is None or (idx is not None and current_tool_index != idx):
                            if current_tool_call:
                                tool_calls.append(current_tool_call)
                            current_tool_index = idx
                            tool_call_id = tool_call.id if tool_call.id else f"call_{len(tool_calls)}_{int(time.time() * 1000)}"
                            current_tool_call = {
                                "id": tool_call_id,
                                "type": "function",
                                "function": {
                                    "name": name_delta or "",
                                    "arguments": args_delta or ""
                                }
                            }
                        else:
                            if name_delta:
                                current_tool_call["function"]["name"] = name_delta
                            if args_delta:
                                current_tool_call["function"]["arguments"] += args_delta

            # Add final tool call if any
            if current_tool_call:
                tool_calls.append(current_tool_call)

            # Process tool calls if any
            if tool_calls:
                yield "\n\n*Processing tool calls...*\n"
                
                # Execute tool calls
                tool_results = []
                for tool_call in tool_calls:
                    try:
                        tool_name = tool_call["function"]["name"]
                        tool_args_str = tool_call["function"]["arguments"]
                        
                        if not tool_name:
                            continue
                        
                        if not tool_args_str or tool_args_str.strip() == "":
                            tool_args = {}
                        else:
                            tool_args = json.loads(tool_args_str)
                        
                        result = await self.call_tool(tool_name, tool_args)
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result
                        })
                    except Exception as e:
                        error_msg = f"Error executing tool {tool_call['function']['name']}: {str(e)}"
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": error_msg
                        })

                # Get final response with tool results
                final_messages = messages.copy()
                final_messages.append({
                    "role": "assistant",
                    "content": "",
                    "tool_calls": tool_calls
                })
                final_messages.extend(tool_results)
                
                final_stream = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=final_messages,
                    max_tokens=1000,
                    timeout=30,
                    stream=True
                )

                for chunk in final_stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            yield error_msg

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
            self.session = None

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return self.conversation_history

    def clear_conversation_history(self):
        """Clear conversation history"""
        self.conversation_history = []
