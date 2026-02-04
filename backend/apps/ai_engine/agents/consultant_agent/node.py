# apps/ai_engine/agents/consultant_agent/node.py
"""
Consultant Agent Node - Nhân viên tư vấn

Sử dụng 2-phase approach cho agents có tools:
1. Phase 1: LLM với tools để thực hiện appointment booking
2. Phase 2: Structured output để format response
"""

from typing import Dict, Any
from langchain_core.messages import SystemMessage, AIMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_consultant_with_tools, llm_flash, logging_node_execution
from apps.ai_engine.agents.schemas import ConsultantResponse
from apps.ai_engine.agents.utils import format_structured_response_to_message
from .prompts import CONSULTANT_PROMPT


def consultant_node(state: AgentState) -> Dict[str, Any]:
    """
    Consultant Agent (Nhân viên tư vấn) - Has Booking Tools
    
    Sử dụng 2-phase approach:
    - Nếu cần gọi tools -> trả về AIMessage với tool_calls
    - Nếu không cần tools -> trả về structured JSON response
    """
    logging_node_execution("CONSULTANT")
    messages = state["messages"]
    prompt = [SystemMessage(content=CONSULTANT_PROMPT)] + messages
    
    # Phase 1: Gọi LLM với tools binding
    response = llm_consultant_with_tools.invoke(prompt)
    
    # Nếu LLM quyết định gọi tool, trả về để LangGraph xử lý
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"[CONSULTANT] Tool calls detected: {[tc['name'] for tc in response.tool_calls]}")
        return {
            "messages": [response],
            "current_agent": "consultant"
        }
    
    # Phase 2: Parse response thành structured format
    try:
        llm_structured = llm_flash.with_structured_output(ConsultantResponse)
        
        format_prompt = [
            SystemMessage(content=f"""Bạn là Consultant Agent. Hãy format lại phản hồi sau thành JSON theo schema yêu cầu.
            
Phản hồi gốc: {response.content}

JSON Schema yêu cầu:
{{
  "thinking_progress": ["Bước 1...", "Bước 2..."],
  "final_response": "Phản hồi đầy đủ...",
  "confidence_score": 0.0-1.0,
  "appointment_info": {{"department": "...", "date": "...", "time_slot": "...", "doctor_name": "..."}} (hoặc null),
  "available_slots": ["slot1", "slot2"] (hoặc null),
  "department_info": "Thông tin khoa phòng",
  "insurance_guidance": "Hướng dẫn bảo hiểm nếu có"
}}""")
        ] + messages
        
        structured_response = llm_structured.invoke(format_prompt)
        
        # Log thinking progress
        print(f"[CONSULTANT] Thinking Progress:")
        for step in structured_response.thinking_progress:
            print(f"  - {step}")
        print(f"[CONSULTANT] Confidence: {structured_response.confidence_score}")
        
        message = format_structured_response_to_message(structured_response, "consultant")
        
    except Exception as e:
        print(f"[CONSULTANT] Structured output error: {e}")
        message = AIMessage(
            content=response.content,
            additional_kwargs={
                "agent": "consultant",
                "thinking_progress": [],
                "structured_response": None
            }
        )
    
    return {
        "messages": [message],
        "current_agent": "consultant"
    }
