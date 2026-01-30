# apps/ai_engine/agents/core_agent/workflow.py

from typing import Dict, Any, Literal
from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field
from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_pro, logging_node_execution
from .prompts import SUPERVISOR_SYSTEM_PROMPT

# ==============================================================================
# STRUCTURED OUTPUT FOR SUPERVISOR
# ==============================================================================

class RouterOutput(BaseModel):
    next_agent: Literal[
        "CONSULTANT", "TRIAGE", "CLINICAL", "PHARMACIST", 
        "PARACLINICAL", "SUMMARIZE", "MARKETING", "HUMAN", "END"
    ] = Field(..., description="The specific worker role to handle the user's request.")

def supervisor_node(state: AgentState) -> Dict[str, Any]:
    logging_node_execution("SUPERVISOR")
    messages = state["messages"]
    supervisor_chain = llm_pro.with_structured_output(RouterOutput)
    prompt_messages = [SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT)] + messages
    
    try:
        decision = supervisor_chain.invoke(prompt_messages)
        next_agent = decision.next_agent.lower()
    except Exception as e:
        print(f"Router Error: {e}")
        next_agent = "CONSULTANT"

    return {"next_agent": next_agent}
