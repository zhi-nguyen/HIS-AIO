"""
AI Engine Graph Module

Multi-Agent architecture for Hospital Information System (HIS)
using LangGraph and Google Gemini models.

Main exports:
- build_agent_graph: Create the compiled graph
- AgentState: State type for the graph
- create_initial_state: Factory for initial state
- run_agent_sync / run_agent_async: Execute the graph
"""

from .state import (
    AgentState,
    PatientContext,
    Message,
    AgentName,
    TriageCode,
    create_initial_state,
)

from .prompts import (
    PromptFactory,
    get_system_prompt,
    GLOBAL_LANGUAGE_RULE,
)

from .nodes import (
    MODEL_CONFIG,
    TEMPERATURE_CONFIG,
    supervisor_node,
    clinical_node_with_escalation,
    triage_node_with_escalation,
    consultant_node,
    pharmacist_node,
    summarize_node,
    marketing_node,
    human_intervention_node,
    end_node,
    NODE_REGISTRY,
    get_node,
)
# ...

__all__ = [
    # State
    "AgentState",
    "PatientContext",
    "Message",
    "AgentName",
    "TriageCode",
    "create_initial_state",
    
    # Prompts
    "PromptFactory",
    "get_system_prompt",
    "GLOBAL_LANGUAGE_RULE",
    
    # Nodes
    "MODEL_CONFIG",
    "TEMPERATURE_CONFIG",
    "supervisor_node",
    "clinical_node_with_escalation",
    "triage_node_with_escalation",
    "consultant_node",
    "pharmacist_node",
    "summarize_node",
    "marketing_node",
    "human_intervention_node",
    "end_node",
    "NODE_REGISTRY",
    "get_node",
    
    # Graph
    "build_agent_graph",
    "create_simple_graph",
    "run_agent_sync",
    "run_agent_async",
    "get_default_graph",
    "get_graph_mermaid",
]
