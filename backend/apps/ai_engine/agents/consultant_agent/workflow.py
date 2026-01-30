# apps/ai_engine/agents/consultant_agent/workflow.py

from typing import Dict, Any
from langchain_core.messages import SystemMessage
from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_consultant_with_tools, logging_node_execution
from .prompts import CONSULTANT_PROMPT

def consultant_node(state: AgentState) -> Dict[str, Any]:
    """Customer Service Agent (Has Tools)"""
    logging_node_execution("CONSULTANT")
    messages = state["messages"]
    prompt = [SystemMessage(content=CONSULTANT_PROMPT)] + messages
    response = llm_consultant_with_tools.invoke(prompt)
    return {"messages": [response]}
