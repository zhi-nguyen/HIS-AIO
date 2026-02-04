# apps/ai_engine/agents/clinical_agent/node.py
"""
Clinical Agent Node - Bác sĩ chẩn đoán

Sử dụng structured output để đảm bảo JSON response với thinking_progress.
"""

from typing import Dict, Any
from langchain_core.messages import SystemMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_pro, logging_node_execution
from apps.ai_engine.agents.schemas import ClinicalResponse
from apps.ai_engine.agents.utils import format_structured_response_to_message
from .prompts import CLINICAL_PROMPT


def clinical_node(state: AgentState) -> Dict[str, Any]:
    """
    Clinical Agent (Bác sĩ chẩn đoán) - Reasoning Focus
    
    Trả về structured JSON với thinking_progress để trace quá trình chẩn đoán.
    """
    logging_node_execution("CLINICAL")
    messages = state["messages"]
    prompt = [SystemMessage(content=CLINICAL_PROMPT)] + messages
    
    try:
        # Sử dụng structured output để đảm bảo JSON
        llm_structured = llm_pro.with_structured_output(ClinicalResponse)
        response = llm_structured.invoke(prompt)
        
        # Log thinking progress cho debug
        print(f"[CLINICAL] Thinking Progress:")
        for step in response.thinking_progress:
            print(f"  - {step}")
        print(f"[CLINICAL] Confidence: {response.confidence_score}")
        print(f"[CLINICAL] Urgent Care: {response.requires_urgent_care}")
        
        # Convert to AIMessage for graph compatibility
        message = format_structured_response_to_message(response, "clinical")
        
    except Exception as e:
        print(f"[CLINICAL] Structured output error: {e}")
        # Fallback to regular response
        from langchain_core.messages import AIMessage
        message = AIMessage(
            content=f"[Lỗi xử lý] Xin vui lòng mô tả lại triệu chứng của bạn.",
            additional_kwargs={"agent": "clinical", "error": str(e)}
        )
    
    return {
        "messages": [message],
        "current_agent": "clinical"
    }
