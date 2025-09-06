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
        
        # Enhanced system prompt based on Blockza template
        self.base_system_prompt = """You are a professional AI assistant for Blockza — a Web3 platform offering AI-powered company directories, partner discovery, and meeting booking.

🎯 Your response must be formatted using clean Bootstrap 5-compatible HTML, styled like https://blockza.io.

⚠️ IMPORTANT:
- Your first priority is to directly and professionally answer the user's question in a clear and well structured way using Bootstrap for it.
- Use bullet points, short paragraphs, and emphasize the benefit of using Blockza features such as directory listings, meeting bookings, visibility, or tools.
- After the main response, you may display "Similar Companies of [CATEGORY]".

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

        # Use the enhanced system prompt for all queries
        system_prompt = self.get_system_prompt()
        
        # Prepare messages with system prompt
        messages = [{
            "role": "system",
            "content": system_prompt
        }]
        
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
        
        return await self._process_messages(messages)

    async def process_query_with_context(self, context_messages: List[Dict[str, Any]]) -> str:
        """Process a query with provided context messages (for chat application)"""
        if not self.session:
            return "Error: Not connected to MCP server"
        
        # Use the enhanced system prompt for all queries
        system_prompt = self.get_system_prompt()
        
        # Prepare messages with system prompt
        messages = [{
            "role": "system",
            "content": system_prompt
        }]
        
        # Add context messages
        messages.extend(context_messages)
        
        return await self._process_messages(messages)

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

    async def _process_messages(self, messages: List[Dict[str, Any]], stream: bool = False) -> str:
        """Internal method to process messages with OpenAI and tools"""

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
                model="gpt-4o",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=1000,
                timeout=30,  # 30 second timeout
                stream=stream
            )

            response_message = response.choices[0].message
            
            # Only add to conversation history if this is a regular query (not context-based)
            if len(messages) == len(self.conversation_history) + 2:  # system + user message
                self.conversation_history.append(response_message)

            # Check if tool calls are needed
            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    # Execute tool call
                    result = await self.session.call_tool(tool_name, tool_args)
                    
                    # Add tool result to conversation (only for regular queries)
                    if len(messages) == len(self.conversation_history) + 2:
                        self.conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result.content[0].text if result.content else "No content returned"
                        })

                # Get final response from OpenAI
                final_messages = messages.copy()
                final_messages.append(response_message)
                
                # Add tool results
                for tool_call in response_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    result = await self.session.call_tool(tool_name, tool_args)
                    final_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result.content[0].text if result.content else "No content returned"
                    })
                
                final_response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=final_messages,
                    max_tokens=1000,
                    timeout=30  # 30 second timeout
                )

                final_message = final_response.choices[0].message
                
                # Only add to conversation history if this is a regular query
                if len(messages) == len(self.conversation_history) + 2:
                    self.conversation_history.append(final_message)
                    
                return final_message.content

            return response_message.content

        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(error_msg)
            # Only clear conversation history on error for regular queries
            if len(messages) == len(self.conversation_history) + 2:
                self.conversation_history = []
            return error_msg

    async def _process_messages_stream(self, messages: List[Dict[str, Any]]):
        """Internal method to stream messages with OpenAI and tools"""
        
        if not self.session:
            yield "Error: Not connected to MCP server"
            return
        
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
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
                
                # Handle tool calls in streaming
                if chunk.choices[0].delta.tool_calls:
                    for tool_call in chunk.choices[0].delta.tool_calls:
                        if tool_call.index is not None:
                            # New tool call
                            if current_tool_call:
                                tool_calls.append(current_tool_call)
                            current_tool_call = {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.function.name if tool_call.function.name else "",
                                    "arguments": tool_call.function.arguments if tool_call.function.arguments else ""
                                }
                            }
                        else:
                            # Continuation of current tool call
                            if current_tool_call and tool_call.function.arguments:
                                current_tool_call["function"]["arguments"] += tool_call.function.arguments

            # Add final tool call if any
            if current_tool_call:
                tool_calls.append(current_tool_call)

            # Process tool calls if any
            if tool_calls:
                yield "\n\n*Processing tool calls...*\n"
                
                # Execute tool calls
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])
                    
                    result = await self.session.call_tool(tool_name, tool_args)
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result.content[0].text if result.content else "No content returned"
                    })

                # Get final response with tool results
                final_messages = messages.copy()
                final_messages.append({
                    "role": "assistant",
                    "content": full_response,
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
