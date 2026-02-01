from typing import Dict, Any
from langchain_core.messages import SystemMessage
from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_flash, logging_node_execution
from .prompts import SUMMARIZE_AGENT_PROMPT

def summarize_node(state: AgentState) -> Dict[str, Any]:
    """Summarize Agent"""
    logging_node_execution("SUMMARIZE")
    messages = state["messages"]
    prompt = [SystemMessage(content=SUMMARIZE_AGENT_PROMPT)] + messages
    response = llm_flash.invoke(prompt)
    return {"messages": [response]}
