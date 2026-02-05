# apps/ai_engine/agents/summarize_agent/node.py
"""
Summarize Agent Node - Tóm tắt bệnh án

REFACTORED cho Real Token Streaming:
- LLM text response trực tiếp (không cần tools)
"""

from typing import Dict, Any, List
import re
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_flash, logging_node_execution
from apps.ai_engine.agents.message_utils import convert_and_filter_messages, log_llm_response
from .prompts import SUMMARIZE_THINKING_PROMPT


def extract_thinking_steps(text: str) -> List[str]:
    """Extract thinking steps từ text."""
    steps = []
    pattern = r'\*\*Bước\s*\d+[^*]*\*\*:?\s*([^\*]+?)(?=\*\*Bước|\*\*Bản Tóm Tắt|$)'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    for i, match in enumerate(matches, 1):
        step_text = match.strip()
        if step_text:
            if len(step_text) > 200:
                step_text = step_text[:200] + "..."
            steps.append(f"Bước {i}: {step_text}")
    
    return steps if steps else ["Đã tóm tắt hồ sơ bệnh án"]


def extract_special_notes(text: str) -> str:
    """Extract special notes từ text."""
    if "[QUAN TRỌNG]" in text:
        pattern = r'\[QUAN TRỌNG\][^\n]*'
        matches = re.findall(pattern, text)
        if matches:
            return " | ".join(matches[:3])
    return None


def summarize_node(state: AgentState) -> Dict[str, Any]:
    """
    Summarize Agent - Real Token Streaming
    
    Flow:
    - LLM text response để tóm tắt hồ sơ
    """
    logging_node_execution("SUMMARIZE")
    messages = state["messages"]
    
    # Convert và filter messages
    converted_messages, last_user_message = convert_and_filter_messages(messages, "SUMMARIZE")
    
    prompt = [SystemMessage(content=SUMMARIZE_THINKING_PROMPT)] + converted_messages
    
    try:
        # Direct LLM invoke (text response)
        response = llm_flash.invoke(prompt)
        
        # Log response
        text_analysis = log_llm_response(response, "SUMMARIZE")
        
        # Extract components từ text
        thinking_steps = extract_thinking_steps(text_analysis)
        special_notes = extract_special_notes(text_analysis)
        
        print(f"[SUMMARIZE] Thinking steps: {len(thinking_steps)}")
        if special_notes:
            print(f"[SUMMARIZE] Special notes: {special_notes[:100]}...")
        
        # Build structured data
        structured_data = {
            "thinking_progress": thinking_steps,
            "final_response": text_analysis,
            "confidence_score": 0.85,
            "special_notes": special_notes,
        }
        
        message = AIMessage(
            content=text_analysis,
            additional_kwargs={
                "agent": "summarize",
                "structured_response": structured_data,
                "thinking_progress": thinking_steps,
            }
        )
        
    except Exception as e:
        print(f"[SUMMARIZE] Error: {e}")
        message = AIMessage(
            content=f"[Lỗi xử lý] Không thể tóm tắt hồ sơ. Vui lòng thử lại.",
            additional_kwargs={"agent": "summarize", "error": str(e)}
        )
    
    return {
        "messages": [message],
        "current_agent": "summarize"
    }
