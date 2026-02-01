from typing import Dict, Any
from langchain_core.messages import SystemMessage
from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_pro, logging_node_execution
from .prompts import CLINICAL_PROMPT

def clinical_node(state: AgentState) -> Dict[str, Any]:
    """Clinical Agent (Reasoning Focus)"""
    logging_node_execution("CLINICAL")
    messages = state["messages"]
    prompt = [SystemMessage(content=CLINICAL_PROMPT)] + messages
    response = llm_pro.invoke(prompt)
    return {"messages": [response]}
