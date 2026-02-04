# apps/ai_engine/agents/core_agent/node.py
"""
Supervisor Node - Routes requests to specialist agents

Sử dụng structured output để đảm bảo JSON response với thinking_progress.
"""

from typing import Dict, Any, Literal
from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_pro, logging_node_execution
from .prompts import SUPERVISOR_SYSTEM_PROMPT

# ==============================================================================
# STRUCTURED OUTPUT FOR SUPERVISOR
# ==============================================================================

class SupervisorOutput(BaseModel):
    """Structured output cho Supervisor với thinking_progress bắt buộc."""
    
    thinking_progress: list[str] = Field(
        ..., 
        min_length=1,
        description="Các bước phân tích ngữ cảnh và quyết định routing"
    )
    next_agent: Literal[
        "CONSULTANT", "TRIAGE", "CLINICAL", "PHARMACIST", 
        "PARACLINICAL", "SUMMARIZE", "MARKETING", "HUMAN", "END"
    ] = Field(..., description="Agent chuyên môn được chọn để xử lý yêu cầu")
    routing_reason: str = Field(
        ..., 
        description="Lý do chọn agent này"
    )


def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    Supervisor node - phân tích và route đến agent phù hợp.
    
    Returns:
        Dict với next_agent và metadata về quyết định routing
    """
    logging_node_execution("SUPERVISOR")
    messages = state["messages"]
    
    # Sử dụng structured output để đảm bảo JSON response
    supervisor_chain = llm_pro.with_structured_output(SupervisorOutput)
    prompt_messages = [SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT)] + messages
    
    try:
        decision = supervisor_chain.invoke(prompt_messages)
        next_agent = decision.next_agent.lower()
        
        # Log thinking progress cho debug
        print(f"[SUPERVISOR] Thinking Progress:")
        for step in decision.thinking_progress:
            print(f"  - {step}")
        print(f"[SUPERVISOR] Routing to: {next_agent}")
        print(f"[SUPERVISOR] Reason: {decision.routing_reason}")
        
    except Exception as e:
        print(f"[SUPERVISOR] Error: {e}")
        print(f"[SUPERVISOR] Fallback to CONSULTANT")
        next_agent = "consultant"

    return {
        "next_agent": next_agent,
        "current_agent": "supervisor"
    }
