# apps/ai_engine/graph/nodes.py

from typing import Literal, Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from pydantic import BaseModel, Field

from .state import AgentState, AgentName
from .prompts import (
    SUPERVISOR_SYSTEM_PROMPT,
    CONSULTANT_PROMPT,
    TRIAGE_PROMPT,
    CLINICAL_PROMPT,
    PHARMACIST_PROMPT,
    SUMMARIZE_AGENT_PROMPT,
    MARKETING_AGENT_PROMPT
)

# IMPORT TOOLS
from .tools import (
    check_appointment_slots, 
    book_appointment, 
    check_drug_interaction,
    suggest_drug_alternative,
    trigger_emergency_alert,
    assess_vital_signs
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

MODEL_CONFIG = {
    "complex": "gemini-2.0-flash", # Using flash for dev, typically pro
    "fast": "gemini-2.0-flash"
}

TEMPERATURE_CONFIG = {
    "creative": 0.7,
    "precise": 0.2
}

# ==============================================================================
# MODELS
# ==============================================================================

# Model for Complex Reasoning (Clinical, Triage, Supervisor)
llm_pro = ChatGoogleGenerativeAI(
    model=MODEL_CONFIG["complex"],
    temperature=TEMPERATURE_CONFIG["precise"],
    convert_system_message_to_human=True
)

# Model for Fast Tasks (Consultant, Marketing, Summarize)
llm_flash = ChatGoogleGenerativeAI(
    model=MODEL_CONFIG["fast"],
    temperature=TEMPERATURE_CONFIG["creative"],
    convert_system_message_to_human=True
)

# ==============================================================================
# TOOLS BINDING
# ==============================================================================

consultant_tools = [check_appointment_slots, book_appointment]
pharmacist_tools = [check_drug_interaction, suggest_drug_alternative]
triage_tools = [trigger_emergency_alert, assess_vital_signs]

llm_consultant_with_tools = llm_flash.bind_tools(consultant_tools)
llm_pharmacist_with_tools = llm_flash.bind_tools(pharmacist_tools)
llm_triage_with_tools = llm_pro.bind_tools(triage_tools)

# ==============================================================================
# STRUCTURED OUTPUT FOR SUPERVISOR
# ==============================================================================

class RouterOutput(BaseModel):
    next_agent: Literal[
        "CONSULTANT", "TRIAGE", "CLINICAL", "PHARMACIST", 
        "SUMMARIZE", "MARKETING", "HUMAN", "END"
    ] = Field(..., description="The specific worker role to handle the user's request.")

# ==============================================================================
# NODE FUNCTIONS
# ==============================================================================

def logging_node_execution(node_name: str):
    """Log execution of a node."""
    print(f"--- Executing Node: {node_name} ---")

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

def consultant_node(state: AgentState) -> Dict[str, Any]:
    """Customer Service Agent (Has Tools)"""
    logging_node_execution("CONSULTANT")
    messages = state["messages"]
    prompt = [SystemMessage(content=CONSULTANT_PROMPT)] + messages
    response = llm_consultant_with_tools.invoke(prompt)
    return {"messages": [response]}

def triage_node(state: AgentState) -> Dict[str, Any]:
    """Triage Agent (Has Alert Tool)"""
    logging_node_execution("TRIAGE")
    messages = state["messages"]
    prompt = [SystemMessage(content=TRIAGE_PROMPT)] + messages
    response = llm_triage_with_tools.invoke(prompt) 
    return {"messages": [response]}

def clinical_node(state: AgentState) -> Dict[str, Any]:
    """Clinical Agent (Reasoning Focus)"""
    logging_node_execution("CLINICAL")
    messages = state["messages"]
    prompt = [SystemMessage(content=CLINICAL_PROMPT)] + messages
    response = llm_pro.invoke(prompt)
    return {"messages": [response]}

def pharmacist_node(state: AgentState) -> Dict[str, Any]:
    """Pharmacist Agent (Has Drug Tools)"""
    logging_node_execution("PHARMACIST")
    messages = state["messages"]
    prompt = [SystemMessage(content=PHARMACIST_PROMPT)] + messages
    response = llm_pharmacist_with_tools.invoke(prompt)
    return {"messages": [response]}

def summarize_node(state: AgentState) -> Dict[str, Any]:
    """Summarize Agent"""
    logging_node_execution("SUMMARIZE")
    messages = state["messages"]
    prompt = [SystemMessage(content=SUMMARIZE_AGENT_PROMPT)] + messages
    response = llm_flash.invoke(prompt)
    return {"messages": [response]}

def marketing_node(state: AgentState) -> Dict[str, Any]:
    """Marketing Agent"""
    logging_node_execution("MARKETING")
    messages = state["messages"]
    prompt = [SystemMessage(content=MARKETING_AGENT_PROMPT)] + messages
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
    "summarize": summarize_node,
    "marketing": marketing_node,
    "human": human_intervention_node
}

def get_node(name: str):
    return NODE_REGISTRY.get(name)