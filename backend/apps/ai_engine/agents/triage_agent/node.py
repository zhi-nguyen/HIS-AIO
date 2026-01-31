from typing import Dict, Any
from langchain_core.messages import SystemMessage
from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_triage_with_tools, logging_node_execution
from .prompts import TRIAGE_PROMPT

def triage_node(state: AgentState) -> Dict[str, Any]:
    """Triage Agent (Has Alert Tool)"""
    logging_node_execution("TRIAGE")
    messages = state["messages"]
    prompt = [SystemMessage(content=TRIAGE_PROMPT)] + messages
    response = llm_triage_with_tools.invoke(prompt) 
    return {"messages": [response]}
