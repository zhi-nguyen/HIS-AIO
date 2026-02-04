# apps/ai_engine/agents/summarize_agent/node.py
"""
Summarize Agent Node - Tóm tắt bệnh án

Sử dụng structured output để đảm bảo JSON response với thinking_progress.
"""

from typing import Dict, Any
from langchain_core.messages import SystemMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_flash, logging_node_execution
from apps.ai_engine.agents.schemas import SummarizeResponse
from apps.ai_engine.agents.utils import format_structured_response_to_message
from .prompts import SUMMARIZE_AGENT_PROMPT


def summarize_node(state: AgentState) -> Dict[str, Any]:
    """
    Summarize Agent - Tóm tắt hồ sơ bệnh án
    
    Trả về structured JSON với thinking_progress để trace quá trình tóm tắt.
    """
    logging_node_execution("SUMMARIZE")
    messages = state["messages"]
    prompt = [SystemMessage(content=SUMMARIZE_AGENT_PROMPT)] + messages
    
    try:
        # Sử dụng structured output để đảm bảo JSON
        llm_structured = llm_flash.with_structured_output(SummarizeResponse)
        response = llm_structured.invoke(prompt)
        
        # Log thinking progress cho debug
        print(f"[SUMMARIZE] Thinking Progress:")
        for step in response.thinking_progress:
            print(f"  - {step}")
        print(f"[SUMMARIZE] Confidence: {response.confidence_score}")
        
        # Convert to AIMessage for graph compatibility
        message = format_structured_response_to_message(response, "summarize")
        
    except Exception as e:
        print(f"[SUMMARIZE] Structured output error: {e}")
        from langchain_core.messages import AIMessage
        message = AIMessage(
            content=f"[Lỗi xử lý] Không thể tóm tắt hồ sơ. Vui lòng thử lại.",
            additional_kwargs={"agent": "summarize", "error": str(e)}
        )
    
    return {
        "messages": [message],
        "current_agent": "summarize"
    }
