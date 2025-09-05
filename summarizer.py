"""
Conversation summarization logic for long conversations.
This module handles creating summaries of older parts of conversations to maintain context.
"""

import re
from typing import List, Dict, Any
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class ConversationSummarizer:
    """Handles summarization of long conversations"""
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.summary_threshold = 20  # Number of messages before summarization
        self.context_limit = 10  # Number of recent messages to keep in context
    
    def should_summarize(self, message_count: int) -> bool:
        """Check if conversation should be summarized"""
        return message_count > self.summary_threshold
    
    def extract_messages_to_summarize(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract messages that should be summarized (exclude recent messages and existing summaries).
        Returns messages that are older than the context limit and not already summaries.
        """
        # Sort messages by timestamp
        sorted_messages = sorted(messages, key=lambda x: x.get('timestamp', ''))
        
        # Get messages to summarize (exclude the last context_limit messages and summaries)
        messages_to_summarize = []
        non_summary_messages = [msg for msg in sorted_messages if not msg.get('is_summary', False)]
        
        if len(non_summary_messages) > self.context_limit:
            messages_to_summarize = non_summary_messages[:-self.context_limit]
        
        return messages_to_summarize
    
    def create_summary(self, messages: List[Dict[str, Any]], conversation_title: str = "") -> str:
        """
        Create a summary of the given messages using OpenAI.
        """
        if not messages:
            return ""
        
        # Prepare messages for summarization
        conversation_text = self._format_messages_for_summarization(messages)
        
        # Create summary prompt
        summary_prompt = f"""
Please create a concise summary of the following conversation. The summary should:

1. Capture the main topics discussed
2. Include key decisions or conclusions reached
3. Preserve important context for future reference
4. Be concise but informative (aim for 2-3 sentences)

Conversation Title: {conversation_title}

Conversation:
{conversation_text}

Summary:
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates concise summaries of conversations."},
                    {"role": "user", "content": summary_prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error creating summary: {e}")
            # Fallback to a simple summary
            return self._create_fallback_summary(messages)
    
    def _format_messages_for_summarization(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages for summarization"""
        formatted_text = ""
        
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            
            # Format timestamp if available
            time_str = f"[{timestamp}] " if timestamp else ""
            
            # Format role
            role_str = {
                'user': 'User',
                'assistant': 'Assistant',
                'system': 'System'
            }.get(role, role.title())
            
            formatted_text += f"{time_str}{role_str}: {content}\n"
        
        return formatted_text
    
    def _create_fallback_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Create a simple fallback summary when OpenAI fails"""
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        assistant_messages = [msg for msg in messages if msg.get('role') == 'assistant']
        
        summary_parts = []
        
        if user_messages:
            summary_parts.append(f"User asked {len(user_messages)} questions")
        
        if assistant_messages:
            summary_parts.append(f"Assistant provided {len(assistant_messages)} responses")
        
        # Include first user message as context
        if user_messages:
            first_question = user_messages[0].get('content', '')[:100]
            if len(first_question) == 100:
                first_question += "..."
            summary_parts.append(f"Started with: {first_question}")
        
        return ". ".join(summary_parts) + "."
    
    def build_context_with_summary(self, conversation_id: int, database_module) -> List[Dict[str, Any]]:
        """
        Build context for a conversation, including summary and recent messages.
        This is the main method that orchestrates the summarization process.
        """
        # Get all messages for the conversation
        all_messages = database_module.get_all_messages_for_conversation(conversation_id)
        
        if not all_messages:
            return []
        
        # Convert to dict format
        messages_dict = [msg.to_dict() for msg in all_messages]
        
        # Check if we need to create a summary
        non_summary_messages = [msg for msg in messages_dict if not msg.get('is_summary', False)]
        
        if len(non_summary_messages) > self.summary_threshold:
            # Check if we already have a recent summary
            existing_summaries = [msg for msg in messages_dict if msg.get('is_summary', False)]
            
            # If no summary exists or the conversation has grown significantly, create a new one
            if not existing_summaries or len(non_summary_messages) > self.summary_threshold * 1.5:
                messages_to_summarize = self.extract_messages_to_summarize(messages_dict)
                
                if messages_to_summarize:
                    # Get conversation title for context
                    conversation = database_module.get_conversation_by_id(conversation_id, email=None)
                    title = conversation.title if conversation else ""
                    
                    # Create summary
                    summary_content = self.create_summary(messages_to_summarize, title)
                    
                    # Save summary to database
                    database_module.create_conversation_summary(conversation_id, summary_content)
        
        # Return context messages (summary + recent messages)
        context_messages = database_module.get_messages_for_context(conversation_id, self.context_limit)
        
        # Convert Message objects to dictionaries
        return [msg.to_dict() for msg in context_messages]
    
    def generate_conversation_title(self, first_message: str) -> str:
        """
        Generate a title for a new conversation based on the first user message.
        """
        if not first_message:
            return "New Conversation"
        
        # Clean the message
        cleaned_message = re.sub(r'[^\w\s]', '', first_message)
        words = cleaned_message.split()
        
        # Take first few words, limit to reasonable length
        if len(words) <= 5:
            title = ' '.join(words)
        else:
            title = ' '.join(words[:5]) + "..."
        
        # Ensure title is not too long
        if len(title) > 50:
            title = title[:47] + "..."
        
        return title or "New Conversation"
