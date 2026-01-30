# apps/ai_engine/agents/marketing_agent/workflow.py

from typing import Dict, Any
from langchain_core.messages import SystemMessage
from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_flash, logging_node_execution
from .prompts import MARKETING_AGENT_PROMPT

def marketing_node(state: AgentState) -> Dict[str, Any]:
    """Marketing Agent"""
    logging_node_execution("MARKETING")
    messages = state["messages"]
    prompt = [SystemMessage(content=MARKETING_AGENT_PROMPT)] + messages
    response = llm_flash.invoke(prompt)
    return {"messages": [response]}
