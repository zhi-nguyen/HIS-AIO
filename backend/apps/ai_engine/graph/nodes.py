# apps/ai_engine/graph/nodes.py

from typing import Dict, Any

# Import from llm_config to maintain backward compatibility if these are imported from here
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

# Import Node Functions from New Agent Modules
from apps.ai_engine.agents.clinical_agent.workflow import clinical_node
from apps.ai_engine.agents.triage_agent.workflow import triage_node
from apps.ai_engine.agents.consultant_agent.workflow import consultant_node
from apps.ai_engine.agents.pharmacist_agent.workflow import pharmacist_node
from apps.ai_engine.agents.paraclinical_agent.workflow import paraclinical_node
from apps.ai_engine.agents.marketing_agent.workflow import marketing_node
from apps.ai_engine.agents.summarize_agent.workflow import summarize_node
from apps.ai_engine.agents.core_agent.workflow import supervisor_node, RouterOutput

from langchain_core.messages import SystemMessage
from .state import AgentState

# ==============================================================================
# NODE FUNCTIONS (Re-exported or Wrappers if needed)
# ==============================================================================

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