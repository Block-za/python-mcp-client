import asyncio
import json
import os
import sys
import time
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
      <div class='card-img-top' style='height: 100px; background: linear-gradient(135deg, #1e5fb3 0%, #764ba2 100%); position: relative; overflow: hidden;'>
        <img src='BANNER_IMAGE_URL' style='width: 100%; height: 100%; object-fit: cover;' alt='Company Banner' onerror='this.style.display="none"'>
        <div style='position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; color: white;'>
          <img src='LOGO_URL' style='width: 40px; height: 40px; border-radius: 6px; margin-bottom: 5px;' alt='Company Logo' onerror='this.style.display="none"'>
          <div style='font-weight: bold; font-size: 16px;'>COMPANY_NAME</div>
        </div>
      </div>
      <div class='card-body'>
        <div class='d-flex align-items-center mb-2'>
          <img src='LOGO_URL' class='me-3' style='width: 40px; height: 40px; border-radius: 6px; object-fit: cover; background: #f8f9fa; border: 1px solid #e9ecef;' alt='Company Logo' onerror='this.style.display="none"'>
          <h5 class='card-title mb-0'>Company Name</h5>
        </div>
        <p class='text-muted small mb-3'>Short company description...</p>
        <div class='d-flex gap-2'>
          <a href='https://blockza.io/directory/COMPANY_SLUG' target='_blank' class='btn btn-primary btn-sm flex-fill'>View Directory</a>
          <a href='WEBSITE_URL' target='_blank' class='btn btn-outline-primary btn-sm flex-fill'>Visit Website</a>
        </div>
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
        
        return await self._process_messages(messages, update_history=True)

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
        
        return await self._process_messages(messages, update_history=False)

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

    async def _process_messages(self, messages: List[Dict[str, Any]], stream: bool = False, update_history: bool = False) -> str:
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
            # Debug: log initial response tool_calls summary
            try:
                print("[MCPClient] First completion received. tool_calls:",
                      [
                          {
                              'id': tc.id,
                              'name': getattr(tc.function, 'name', None),
                          } for tc in (response_message.tool_calls or [])
                      ])
            except Exception as _:
                pass
            
            # Check if tool calls are needed
            if response_message.tool_calls:
                # Add assistant message with tool_calls to conversation history FIRST (only for regular queries)
                if update_history:
                    # Convert to dictionary format for conversation history
                    assistant_msg = {
                        "role": "assistant",
                        "content": response_message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            } for tc in response_message.tool_calls
                        ] if response_message.tool_calls else None
                    }
                    self.conversation_history.append(assistant_msg)
                
                # Get final response from OpenAI
                final_messages = messages.copy()
                final_messages.append(response_message)
                
                # Execute tool calls and add results
                for tool_call in response_message.tool_calls:
                    tool_name = tool_call.function.name
                    
                    # Skip tool calls with empty function names
                    if not tool_name:
                        continue
                        
                    tool_args = json.loads(tool_call.function.arguments)
                    result = await self.session.call_tool(tool_name, tool_args)
                    
                    tool_result = {
                        "role": "tool",
                        "tool_call_id": tool_call.id if tool_call.id else f"call_{int(time.time() * 1000)}",
                        "content": result.content[0].text if result.content else "No content returned"
                    }
                    
                    # Add tool result to final messages
                    final_messages.append(tool_result)
                    
                    # Add tool result to conversation history (only for regular queries)
                    if update_history:
                        self.conversation_history.append(tool_result)
                
                final_response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=final_messages,
                    max_tokens=1000,
                    timeout=30  # 30 second timeout
                )
                try:
                    print("[MCPClient] Second completion messages roles:", [m.get('role', 'obj') if isinstance(m, dict) else getattr(m, 'role', 'obj') for m in final_messages])
                except Exception:
                    pass

                final_message = final_response.choices[0].message
                
                # Only add to conversation history if this is a regular query
                if update_history:
                    # Convert to dictionary format for conversation history
                    final_assistant_msg = {
                        "role": "assistant",
                        "content": final_message.content
                    }
                    self.conversation_history.append(final_assistant_msg)
                    
                return final_message.content
            else:
                # No tool calls - add assistant message to conversation history (only for regular queries)
                if update_history:
                    # Convert to dictionary format for conversation history
                    assistant_msg = {
                        "role": "assistant",
                        "content": response_message.content
                    }
                    self.conversation_history.append(assistant_msg)

            return response_message.content

        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(error_msg)
            # Only clear conversation history on error for regular queries
            if update_history:
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
            current_tool_index = None
            
            for chunk in stream:
                try:
                    if chunk.choices[0].delta.tool_calls:
                        print("[MCPClient][stream] delta.tool_calls frame:", chunk.choices[0].delta.tool_calls)
                except Exception:
                    pass
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
                
                # Handle tool calls in streaming
                if chunk.choices[0].delta.tool_calls:
                    for tool_call in chunk.choices[0].delta.tool_calls:
                        idx = tool_call.index
                        name_delta = tool_call.function.name if tool_call.function else None
                        args_delta = tool_call.function.arguments if tool_call.function else None

                        # Start a new tool call only if index changes or there is no active call
                        if current_tool_call is None or (idx is not None and current_tool_index is None) or (idx is not None and idx != current_tool_index):
                            # If we were building one, push it
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
                            # Continuation of the same tool call
                            if name_delta:
                                current_tool_call["function"]["name"] = name_delta
                            if args_delta:
                                current_tool_call["function"]["arguments"] += args_delta

            # Add final tool call if any
            if current_tool_call:
                tool_calls.append(current_tool_call)

            # Deduplicate tool_calls by id (some providers repeat frames with the same index)
            if tool_calls:
                unique = {}
                for tc in tool_calls:
                    tc_id = tc["id"]
                    if tc_id not in unique:
                        unique[tc_id] = tc
                    else:
                        # Merge arguments if duplicated
                        unique[tc_id]["function"]["arguments"] += tc["function"].get("arguments", "")
                        # Prefer the non-empty name
                        if not unique[tc_id]["function"].get("name") and tc["function"].get("name"):
                            unique[tc_id]["function"]["name"] = tc["function"]["name"]
                tool_calls = list(unique.values())

            # Process tool calls if any
            if tool_calls:
                yield "\n\n*Processing tool calls...*\n"
                
                # Execute tool calls
                tool_results = []
                for tool_call in tool_calls:
                    try:
                        tool_name = tool_call["function"]["name"]
                        tool_args_str = tool_call["function"]["arguments"]
                        
                        # Skip tool calls with empty function names
                        if not tool_name:
                            continue
                        
                        # Validate and parse tool arguments
                        if not tool_args_str or tool_args_str.strip() == "":
                            tool_args = {}
                        else:
                            tool_args = json.loads(tool_args_str)
                        
                        result = await self.session.call_tool(tool_name, tool_args)
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result.content[0].text if result.content else "No content returned"
                        })
                    except json.JSONDecodeError as e:
                        error_msg = f"Error parsing tool arguments for {tool_call['function']['name']}: {str(e)}"
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": error_msg
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
                
                # Format tool_calls properly for OpenAI API
                formatted_tool_calls = []
                for tool_call in tool_calls:
                    # Ensure name exists
                    if not tool_call["function"].get("name"):
                        continue
                    formatted_tool_calls.append({
                        "id": tool_call["id"],
                        "type": "function",
                        "function": {
                            "name": tool_call["function"]["name"],
                            "arguments": tool_call["function"].get("arguments", "{}") or "{}"
                        }
                    })
                
                # Per OpenAI Chat Completions spec, assistant messages that initiate tool calls
                # should have an empty content and include tool_calls. The natural language
                # content has already been streamed to the client in chunks.
                assistant_message_with_tools = {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": formatted_tool_calls
                }
                
                final_messages.append(assistant_message_with_tools)
                # Only include tool results that reference an id from assistant_message_with_tools
                valid_ids = {tc["id"] for tc in formatted_tool_calls}
                for tr in tool_results:
                    if tr["tool_call_id"] in valid_ids:
                        final_messages.append(tr)
                try:
                    print("[MCPClient][stream] building final turn. assistant tool_calls:", [tc['function']['name'] for tc in formatted_tool_calls])
                except Exception:
                    pass
                
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
