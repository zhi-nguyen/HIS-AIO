# apps/ai_engine/agents/marketing_agent/node.py
"""
Marketing Agent Node - Marketing y tế

Sử dụng structured output để đảm bảo JSON response với thinking_progress.
"""

from typing import Dict, Any
from langchain_core.messages import SystemMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_flash, logging_node_execution
from apps.ai_engine.agents.schemas import MarketingResponse
from apps.ai_engine.agents.utils import format_structured_response_to_message
from .prompts import MARKETING_AGENT_PROMPT


def marketing_node(state: AgentState) -> Dict[str, Any]:
    """
    Marketing Agent - Tạo nội dung marketing y tế
    
    Trả về structured JSON với thinking_progress để trace quá trình sáng tạo.
    """
    logging_node_execution("MARKETING")
    messages = state["messages"]
    prompt = [SystemMessage(content=MARKETING_AGENT_PROMPT)] + messages
    
    try:
        # Sử dụng structured output để đảm bảo JSON
        llm_structured = llm_flash.with_structured_output(MarketingResponse)
        response = llm_structured.invoke(prompt)
        
        # Log thinking progress cho debug
        print(f"[MARKETING] Thinking Progress:")
        for step in response.thinking_progress:
            print(f"  - {step}")
        print(f"[MARKETING] Content Type: {response.content_type}")
        print(f"[MARKETING] Confidence: {response.confidence_score}")
        
        # Convert to AIMessage for graph compatibility
        message = format_structured_response_to_message(response, "marketing")
        
    except Exception as e:
        print(f"[MARKETING] Structured output error: {e}")
        from langchain_core.messages import AIMessage
        message = AIMessage(
            content=f"[Lỗi xử lý] Không thể tạo nội dung. Vui lòng thử lại.",
            additional_kwargs={"agent": "marketing", "error": str(e)}
        )
    
    return {
        "messages": [message],
        "current_agent": "marketing"
    }
