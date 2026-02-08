# apps/ai_engine/agents/marketing_agent/node.py
"""
Marketing Agent Node - Marketing y tế

REFACTORED cho Real Token Streaming:
- LLM text response trực tiếp (không cần tools)
"""

from typing import Dict, Any, List
import re
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_flash, logging_node_execution
from apps.ai_engine.agents.message_utils import convert_and_filter_messages, log_llm_response, extract_final_response
from .prompts import MARKETING_THINKING_PROMPT


def extract_thinking_steps(text: str) -> List[str]:
    """Extract thinking steps từ text."""
    steps = []
    pattern = r'\*\*Bước\s*\d+[^*]*\*\*:?\s*([^\*]+?)(?=\*\*Bước|\*\*Nội dung|$)'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    for i, match in enumerate(matches, 1):
        step_text = match.strip()
        if step_text:
            if len(step_text) > 200:
                step_text = step_text[:200] + "..."
            steps.append(f"Bước {i}: {step_text}")
    
    return steps if steps else ["Đã tạo nội dung marketing"]


def extract_content_type(text: str) -> str:
    """Extract content type từ text."""
    text_lower = text.lower()
    if "facebook" in text_lower or "instagram" in text_lower or "social" in text_lower:
        return "social_media"
    elif "email" in text_lower:
        return "email"
    elif "bài viết" in text_lower or "article" in text_lower:
        return "article"
    elif "ưu đãi" in text_lower or "khuyến mãi" in text_lower:
        return "promotion"
    elif "mẹo" in text_lower or "tip" in text_lower:
        return "health_tip"
    return "social_media"


def marketing_node(state: AgentState) -> Dict[str, Any]:
    """
    Marketing Agent - Real Token Streaming
    
    Flow:
    - LLM text response để tạo nội dung marketing
    """
    logging_node_execution("MARKETING")
    messages = state["messages"]
    
    # Convert và filter messages
    converted_messages, last_user_message = convert_and_filter_messages(messages, "MARKETING")
    
    prompt = [SystemMessage(content=MARKETING_THINKING_PROMPT)] + converted_messages
    
    try:
        # Direct LLM invoke (text response)
        response = llm_flash.invoke(prompt)
        
        # Log response
        text_analysis = log_llm_response(response, "MARKETING")
        
        # Extract components từ text
        thinking_steps = extract_thinking_steps(text_analysis)
        content_type = extract_content_type(text_analysis)
        
        print(f"[MARKETING] Thinking steps: {len(thinking_steps)}")
        print(f"[MARKETING] Content type: {content_type}")
        
        # Build structured data
        structured_data = {
            "thinking_progress": thinking_steps,
            "final_response": extract_final_response(text_analysis, "Nội dung Marketing"),
            "confidence_score": 0.85,
            "content_type": content_type,
        }
        
        message = AIMessage(
            content=text_analysis,
            additional_kwargs={
                "agent": "marketing",
                "structured_response": structured_data,
                "thinking_progress": thinking_steps,
            }
        )
        
    except Exception as e:
        print(f"[MARKETING] Error: {e}")
        message = AIMessage(
            content=f"[Lỗi xử lý] Không thể tạo nội dung. Vui lòng thử lại.",
            additional_kwargs={"agent": "marketing", "error": str(e)}
        )
    
    return {
        "messages": [message],
        "current_agent": "marketing"
    }
