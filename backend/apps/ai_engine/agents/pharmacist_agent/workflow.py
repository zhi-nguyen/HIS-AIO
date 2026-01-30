# apps/ai_engine/agents/pharmacist_agent/workflow.py

from typing import Dict, Any
from langchain_core.messages import SystemMessage
from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_pharmacist_with_tools, logging_node_execution
from .prompts import PHARMACIST_PROMPT

def pharmacist_node(state: AgentState) -> Dict[str, Any]:
    """Pharmacist Agent (Has Drug Tools)"""
    logging_node_execution("PHARMACIST")
    messages = state["messages"]
    prompt = [SystemMessage(content=PHARMACIST_PROMPT)] + messages
    response = llm_pharmacist_with_tools.invoke(prompt)
    return {"messages": [response]}
