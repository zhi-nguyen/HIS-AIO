# apps/ai_engine/agents/paraclinical_agent/node.py
"""
Paraclinical Agent Node - Điều phối viên cận lâm sàng

Sử dụng 2-phase approach cho agents có tools:
1. Phase 1: LLM với tools để thực hiện lab/imaging operations
2. Phase 2: Structured output để format response
"""

from typing import Dict, Any
from langchain_core.messages import SystemMessage, AIMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_paraclinical_with_tools, llm_pro, logging_node_execution
from apps.ai_engine.agents.schemas import ParaclinicalResponse
from apps.ai_engine.agents.utils import format_structured_response_to_message
from .prompts import PARACLINICAL_PROMPT


def paraclinical_node(state: AgentState) -> Dict[str, Any]:
    """
    Paraclinical Agent (Điều Phối Viên Cận Lâm Sàng)
    
    Handles:
    - Ordering Workflow: Receive orders, check contraindications, track samples
    - Analysis & Alerting: Critical values, trend analysis
    - Data Normalization: Standardize lab results, extract imaging conclusions
    
    Sử dụng 2-phase approach cho tool compatibility.
    """
    logging_node_execution("PARACLINICAL")
    messages = state["messages"]
    prompt = [SystemMessage(content=PARACLINICAL_PROMPT)] + messages
    
    # Phase 1: Gọi LLM với tools binding
    response = llm_paraclinical_with_tools.invoke(prompt)
    
    # Nếu LLM quyết định gọi tool, trả về để LangGraph xử lý
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"[PARACLINICAL] Tool calls detected: {[tc['name'] for tc in response.tool_calls]}")
        return {
            "messages": [response],
            "current_agent": "paraclinical"
        }
    
    # Phase 2: Parse response thành structured format
    try:
        llm_structured = llm_pro.with_structured_output(ParaclinicalResponse)
        
        format_prompt = [
            SystemMessage(content=f"""Bạn là Paraclinical Agent. Hãy format lại phản hồi sau thành JSON theo schema yêu cầu.
            
Phản hồi gốc: {response.content}

JSON Schema yêu cầu:
{{
  "thinking_progress": ["Bước 1...", "Bước 2..."],
  "final_response": "Phản hồi đầy đủ...",
  "confidence_score": 0.0-1.0,
  "order_status": "ORDER_PENDING|APPROVED|REJECTED|IN_PROGRESS|COMPLETED" (hoặc null),
  "critical_values": [
    {{"test_name": "...", "value": "...", "unit": "...", "normal_range": "...", "status": "CRITICAL_HIGH|LOW|PANIC|NORMAL"}}
  ],
  "contraindication_found": true/false,
  "contraindication_details": "Chi tiết nếu có",
  "trend_analysis": "Phân tích xu hướng nếu có",
  "trigger_critical_alert": true/false
}}""")
        ] + messages
        
        structured_response = llm_structured.invoke(format_prompt)
        
        # Log thinking progress
        print(f"[PARACLINICAL] Thinking Progress:")
        for step in structured_response.thinking_progress:
            print(f"  - {step}")
        print(f"[PARACLINICAL] Confidence: {structured_response.confidence_score}")
        if structured_response.critical_values:
            print(f"[PARACLINICAL] Critical values: {len(structured_response.critical_values)}")
        print(f"[PARACLINICAL] Trigger alert: {structured_response.trigger_critical_alert}")
        
        message = format_structured_response_to_message(structured_response, "paraclinical")
        
    except Exception as e:
        print(f"[PARACLINICAL] Structured output error: {e}")
        message = AIMessage(
            content=response.content,
            additional_kwargs={
                "agent": "paraclinical",
                "thinking_progress": [],
                "structured_response": None
            }
        )
    
    return {
        "messages": [message],
        "current_agent": "paraclinical"
    }
