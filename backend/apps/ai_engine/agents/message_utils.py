# apps/ai_engine/agents/message_utils.py
"""
Shared utility functions for message conversion and filtering.

Các agent node dùng chung utility này để:
1. Convert dict messages sang LangChain format (HumanMessage, AIMessage, SystemMessage)
2. Filter out các AIMessage cũ có JSON content để tránh confuse LLM
"""

from typing import List, Any, Tuple
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


def convert_and_filter_messages(messages: List[Any], agent_name: str = "AGENT") -> Tuple[List[Any], str]:
    """
    Convert dict messages sang LangChain format và filter out JSON AI responses cũ.
    
    Args:
        messages: List of messages (có thể là dict hoặc LangChain message objects)
        agent_name: Tên agent để logging
    
    Returns:
        Tuple[converted_messages, last_user_message]
        - converted_messages: List các LangChain message objects
        - last_user_message: Nội dung tin nhắn user cuối cùng
    
    Example:
        converted, user_msg = convert_and_filter_messages(state["messages"], "PHARMACIST")
        prompt = [SystemMessage(content=PROMPT)] + converted
    """
    # Debug logging
    print(f"[{agent_name}] Number of messages: {len(messages)}")
    for i, msg in enumerate(messages):
        msg_type = type(msg).__name__
        content = getattr(msg, 'content', '')[:100] if hasattr(msg, 'content') else 'N/A'
        print(f"[{agent_name}] Message {i}: type={msg_type}, content_preview={content}")
    
    # Convert và filter messages
    converted_messages = []
    last_user_message = ""
    
    for msg in messages:
        if isinstance(msg, HumanMessage):
            # Keep user messages
            converted_messages.append(msg)
            last_user_message = msg.content
        elif isinstance(msg, AIMessage):
            # Skip AIMessage nếu content là JSON hoặc rỗng (response cũ từ agent)
            content = msg.content or ""
            if content.startswith("```") or content.startswith("{") or len(content) < 10:
                print(f"[{agent_name}] Skipping old AIMessage: {content[:50]}...")
                continue
            # Keep AI messages with actual text content (conversation history)
            converted_messages.append(msg)
        elif isinstance(msg, SystemMessage):
            converted_messages.append(msg)
        elif isinstance(msg, dict):
            # Convert dict to appropriate message type
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if not content:
                continue  # Skip empty messages
            if role == 'user':
                converted_messages.append(HumanMessage(content=content))
                last_user_message = content
            elif role == 'assistant':
                # Skip assistant messages that look like JSON
                if content.startswith("```") or content.startswith("{"):
                    print(f"[{agent_name}] Skipping JSON assistant message: {content[:50]}...")
                    continue
                converted_messages.append(AIMessage(content=content))
            elif role == 'system':
                converted_messages.append(SystemMessage(content=content))
            else:
                converted_messages.append(HumanMessage(content=content))
                if role == 'user':
                    last_user_message = content
        else:
            content = getattr(msg, 'content', str(msg))
            if content:
                converted_messages.append(HumanMessage(content=content))
    
    print(f"[{agent_name}] Converted {len(converted_messages)} messages to LangChain format")
    
    # Ensure we have at least one user message
    if not any(isinstance(m, HumanMessage) for m in converted_messages):
        print(f"[{agent_name}] WARNING: No user message found in converted messages!")
        # Try to find user message from original messages
        for msg in messages:
            if isinstance(msg, dict) and msg.get('role') == 'user':
                content = msg.get('content', '')
                converted_messages.append(HumanMessage(content=content))
                last_user_message = content
                break
    
    print(f"[{agent_name}] Last user message: {last_user_message[:100] if last_user_message else '(empty)'}")
    
    return converted_messages, last_user_message


def log_llm_response(response: Any, agent_name: str = "AGENT") -> str:
    """
    Log và trả về response content từ LLM.
    
    Args:
        response: Response từ LLM invoke
        agent_name: Tên agent để logging
    
    Returns:
        Response content string
    """
    content = response.content if hasattr(response, 'content') else str(response)
    print(f"[{agent_name}] Response length: {len(content)} chars")
    print(f"[{agent_name}] Response preview: {content[:200] if content else '(empty)'}...")
    return content
