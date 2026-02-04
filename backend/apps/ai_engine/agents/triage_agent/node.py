# apps/ai_engine/agents/triage_agent/node.py
"""
Triage Agent Node - Điều dưỡng phân luồng

Sử dụng 2-phase approach cho agents có tools:
1. Phase 1: LLM với tools để thực hiện actions
2. Phase 2: Structured output để format response
"""

from typing import Dict, Any
from langchain_core.messages import SystemMessage, AIMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_triage_with_tools, llm_pro, logging_node_execution
from apps.ai_engine.agents.schemas import TriageResponse
from apps.ai_engine.agents.utils import format_structured_response_to_message
from .prompts import TRIAGE_PROMPT


def triage_node(state: AgentState) -> Dict[str, Any]:
    """
    Triage Agent (Điều dưỡng phân luồng) - Has Alert Tools
    
    Sử dụng 2-phase approach:
    - Nếu cần gọi tools -> trả về AIMessage với tool_calls (LangGraph sẽ xử lý)
    - Nếu không cần tools -> trả về structured JSON response
    """
    logging_node_execution("TRIAGE")
    messages = state["messages"]
    prompt = [SystemMessage(content=TRIAGE_PROMPT)] + messages
    
    # Phase 1: Gọi LLM với tools binding
    response = llm_triage_with_tools.invoke(prompt)
    
    # Nếu LLM quyết định gọi tool, trả về để LangGraph xử lý tool calls
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"[TRIAGE] Tool calls detected: {[tc['name'] for tc in response.tool_calls]}")
        return {
            "messages": [response],
            "current_agent": "triage"
        }
    
    # Phase 2: Nếu không có tool calls, parse response thành structured format
    try:
        # Thử parse response content thành structured output
        llm_structured = llm_pro.with_structured_output(TriageResponse)
        
        # Tạo prompt yêu cầu format lại response
        format_prompt = [
            SystemMessage(content=f"""Bạn là Triage Agent. Hãy format lại phản hồi sau thành JSON theo schema yêu cầu.
            
Phản hồi gốc: {response.content}

JSON Schema yêu cầu:
{{
  "thinking_progress": ["Bước 1...", "Bước 2..."],
  "final_response": "Phản hồi đầy đủ...",
  "confidence_score": 0.0-1.0,
  "triage_code": "CODE_GREEN|CODE_YELLOW|CODE_RED|CODE_BLUE",
  "vital_signs_analysis": "Phân tích...",
  "recommended_department": "Khoa...",
  "time_to_treatment": "Thời gian...",
  "trigger_alert": true/false
}}""")
        ] + messages
        
        structured_response = llm_structured.invoke(format_prompt)
        
        # Log thinking progress
        print(f"[TRIAGE] Thinking Progress:")
        for step in structured_response.thinking_progress:
            print(f"  - {step}")
        print(f"[TRIAGE] Triage Code: {structured_response.triage_code}")
        print(f"[TRIAGE] Confidence: {structured_response.confidence_score}")
        
        message = format_structured_response_to_message(structured_response, "triage")
        
    except Exception as e:
        print(f"[TRIAGE] Structured output error: {e}")
        # Fallback: sử dụng response gốc
        message = AIMessage(
            content=response.content,
            additional_kwargs={
                "agent": "triage",
                "thinking_progress": [],
                "structured_response": None
            }
        )
    
    return {
        "messages": [message],
        "current_agent": "triage"
    }
