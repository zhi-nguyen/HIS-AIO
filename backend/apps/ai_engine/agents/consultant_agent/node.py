# apps/ai_engine/agents/consultant_agent/node.py
"""
Consultant Agent Node - Nhân viên tư vấn

REFACTORED cho Real Token Streaming:
- Phase 1: LLM với tools để booking
- Phase 2: Text response nếu không cần tools
"""

from typing import Dict, Any, List
import re
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_consultant_with_tools, logging_node_execution
from apps.ai_engine.agents.message_utils import convert_and_filter_messages, log_llm_response, extract_final_response
from .prompts import CONSULTANT_THINKING_PROMPT


def extract_thinking_steps(text: str) -> List[str]:
    """Extract thinking steps từ text với format **Bước X:**"""
    steps = []
    pattern = r'\*\*Bước\s*\d+[^*]*\*\*:?\s*([^\*]+?)(?=\*\*Bước|\*\*Phản hồi|$)'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    for i, match in enumerate(matches, 1):
        step_text = match.strip()
        if step_text:
            if len(step_text) > 200:
                step_text = step_text[:200] + "..."
            steps.append(f"Bước {i}: {step_text}")
    
    return steps if steps else ["Đã xử lý yêu cầu tư vấn"]


def extract_department_info(text: str) -> str:
    """Extract department info từ text."""
    pattern = r'(Khoa\s+\w+[^,\n]*|tầng\s+\d+[^,\n]*|phòng\s+\d+[^,\n]*)'
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        return ", ".join(matches[:3])
    return None


def consultant_node(state: AgentState) -> Dict[str, Any]:
    """
    Consultant Agent (Nhân viên tư vấn) - Real Token Streaming
    
    Flow:
    1. Nếu cần tools -> return tool calls
    2. LLM text response cho tư vấn thông thường
    """
    logging_node_execution("CONSULTANT")
    messages = state["messages"]
    
    # Convert và filter messages
    converted_messages, last_user_message = convert_and_filter_messages(messages, "CONSULTANT")
    
    prompt = [SystemMessage(content=CONSULTANT_THINKING_PROMPT)] + converted_messages
    
    # Phase 1: Gọi LLM với tools binding
    response = llm_consultant_with_tools.invoke(prompt)
    
    # Nếu LLM quyết định gọi tool
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"[CONSULTANT] Tool calls detected: {[tc['name'] for tc in response.tool_calls]}")
        return {
            "messages": [response],
            "current_agent": "consultant"
        }
    
    # Log response
    text_analysis = log_llm_response(response, "CONSULTANT")
    
    try:
        # Extract components từ text
        thinking_steps = extract_thinking_steps(text_analysis)
        department_info = extract_department_info(text_analysis)
        
        print(f"[CONSULTANT] Thinking steps: {len(thinking_steps)}")
        
        # Build structured data
        structured_data = {
            "thinking_progress": thinking_steps,
            "final_response": extract_final_response(text_analysis, "Phản hồi cho khách hàng"),
            "confidence_score": 0.85,
            "department_info": department_info,
        }
        
        message = AIMessage(
            content=text_analysis,
            additional_kwargs={
                "agent": "consultant",
                "structured_response": structured_data,
                "thinking_progress": thinking_steps,
            }
        )
        
    except Exception as e:
        print(f"[CONSULTANT] Error: {e}")
        message = AIMessage(
            content=text_analysis,
            additional_kwargs={"agent": "consultant", "error": str(e)}
        )
    
    return {
        "messages": [message],
        "current_agent": "consultant"
    }
