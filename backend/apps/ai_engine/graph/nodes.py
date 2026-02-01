# apps/ai_engine/graph/nodes.py

from typing import Dict, Any
from langchain_core.messages import SystemMessage

from .state import AgentState
from .llm_config import (
    logging_node_execution,
    consultant_tools,
    pharmacist_tools,
    triage_tools,
    paraclinical_tools
)

# Import Nodes from agent directories
from apps.ai_engine.agents.core_agent.node import supervisor_node
from apps.ai_engine.agents.clinical_agent.node import clinical_node
from apps.ai_engine.agents.triage_agent.node import triage_node
from apps.ai_engine.agents.consultant_agent.node import consultant_node
from apps.ai_engine.agents.pharmacist_agent.node import pharmacist_node
from apps.ai_engine.agents.paraclinical_agent.node import paraclinical_node
from apps.ai_engine.agents.marketing_agent.node import marketing_node
from apps.ai_engine.agents.summarize_agent.node import summarize_node

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