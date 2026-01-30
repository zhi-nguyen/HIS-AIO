# apps/ai_engine/graph/nodes.py

from typing import Dict, Any, Literal
from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field

from .state import AgentState
from .llm_config import (
    llm_pro, 
    llm_flash, 
    llm_consultant_with_tools, 
    llm_pharmacist_with_tools, 
    llm_triage_with_tools,
    llm_paraclinical_with_tools,
    logging_node_execution,
    MODEL_CONFIG,
    TEMPERATURE_CONFIG,
    consultant_tools,
    pharmacist_tools,
    triage_tools,
    paraclinical_tools
)

# Import PROMPTS from agent directories
from apps.ai_engine.agents.clinical_agent.prompts import CLINICAL_PROMPT
from apps.ai_engine.agents.triage_agent.prompts import TRIAGE_PROMPT
from apps.ai_engine.agents.consultant_agent.prompts import CONSULTANT_PROMPT
from apps.ai_engine.agents.pharmacist_agent.prompts import PHARMACIST_PROMPT
from apps.ai_engine.agents.paraclinical_agent.prompts import PARACLINICAL_PROMPT
from apps.ai_engine.agents.marketing_agent.prompts import MARKETING_AGENT_PROMPT
from apps.ai_engine.agents.summarize_agent.prompts import SUMMARIZE_AGENT_PROMPT
from apps.ai_engine.agents.core_agent.prompts import SUPERVISOR_SYSTEM_PROMPT

# ==============================================================================
# STRUCTURED OUTPUT FOR SUPERVISOR
# ==============================================================================

class RouterOutput(BaseModel):
    next_agent: Literal[
        "CONSULTANT", "TRIAGE", "CLINICAL", "PHARMACIST", 
        "PARACLINICAL", "SUMMARIZE", "MARKETING", "HUMAN", "END"
    ] = Field(..., description="The specific worker role to handle the user's request.")

# ==============================================================================
# NODE FUNCTIONS
# ==============================================================================

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

def clinical_node(state: AgentState) -> Dict[str, Any]:
    """Clinical Agent (Reasoning Focus)"""
    logging_node_execution("CLINICAL")
    messages = state["messages"]
    prompt = [SystemMessage(content=CLINICAL_PROMPT)] + messages
    response = llm_pro.invoke(prompt)
    return {"messages": [response]}

def triage_node(state: AgentState) -> Dict[str, Any]:
    """Triage Agent (Has Alert Tool)"""
    logging_node_execution("TRIAGE")
    messages = state["messages"]
    prompt = [SystemMessage(content=TRIAGE_PROMPT)] + messages
    response = llm_triage_with_tools.invoke(prompt) 
    return {"messages": [response]}

def consultant_node(state: AgentState) -> Dict[str, Any]:
    """Customer Service Agent (Has Tools)"""
    logging_node_execution("CONSULTANT")
    messages = state["messages"]
    prompt = [SystemMessage(content=CONSULTANT_PROMPT)] + messages
    response = llm_consultant_with_tools.invoke(prompt)
    return {"messages": [response]}

def pharmacist_node(state: AgentState) -> Dict[str, Any]:
    """Pharmacist Agent (Has Drug Tools)"""
    logging_node_execution("PHARMACIST")
    messages = state["messages"]
    prompt = [SystemMessage(content=PHARMACIST_PROMPT)] + messages
    response = llm_pharmacist_with_tools.invoke(prompt)
    return {"messages": [response]}

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

def marketing_node(state: AgentState) -> Dict[str, Any]:
    """Marketing Agent"""
    logging_node_execution("MARKETING")
    messages = state["messages"]
    prompt = [SystemMessage(content=MARKETING_AGENT_PROMPT)] + messages
    response = llm_flash.invoke(prompt)
    return {"messages": [response]}

def summarize_node(state: AgentState) -> Dict[str, Any]:
    """Summarize Agent"""
    logging_node_execution("SUMMARIZE")
    messages = state["messages"]
    prompt = [SystemMessage(content=SUMMARIZE_AGENT_PROMPT)] + messages
    response = llm_flash.invoke(prompt)
    return {"messages": [response]}

def human_intervention_node(state: AgentState) -> Dict[str, Any]:
    """Node for handling human escalation"""
    logging_node_execution("HUMAN_ESCALATION")
    return {"messages": [SystemMessage(content="Requesting Human Intervention...")]}

def end_node(state: AgentState) -> Dict[str, Any]:
    """End node (cleanup)"""
    return {}

# ==============================================================================
# ALIASES & REGISTRY
# ==============================================================================

# Aliases for graph builder compatibility
clinical_node_with_escalation = clinical_node
triage_node_with_escalation = triage_node

# Helper for retrieving nodes dynamically if needed
NODE_REGISTRY = {
    "supervisor": supervisor_node,
    "clinical": clinical_node,
    "triage": triage_node,
    "consultant": consultant_node,
    "pharmacist": pharmacist_node,
    "paraclinical": paraclinical_node,
    "summarize": summarize_node,
    "marketing": marketing_node,
    "human": human_intervention_node
}

def get_node(name: str):
    return NODE_REGISTRY.get(name)