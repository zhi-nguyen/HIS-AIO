from typing import Dict, Any
from langchain_core.messages import SystemMessage
from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_paraclinical_with_tools, logging_node_execution
from .prompts import PARACLINICAL_PROMPT

def paraclinical_node(state: AgentState) -> Dict[str, Any]:
    """
    Paraclinical Agent (Điều Phối Viên Cận Lâm Sàng)
    
    Handles:
    - Ordering Workflow: Receive orders, check contraindications, track samples
    - Analysis & Alerting: Critical values, trend analysis
    - Data Normalization: Standardize lab results, extract imaging conclusions
    """
    logging_node_execution("PARACLINICAL")
    messages = state["messages"]
    prompt = [SystemMessage(content=PARACLINICAL_PROMPT)] + messages
    response = llm_paraclinical_with_tools.invoke(prompt)
    return {"messages": [response]}
