"""
AI Engine Graph Module

Multi-Agent architecture for Hospital Information System (HIS)
using LangGraph and Google Gemini models.

Main exports:
- build_agent_graph: Create the compiled graph
- AgentState: State type for the graph
- create_initial_state: Factory for initial state
- run_agent_sync / run_agent_async: Execute the graph

NOTE: Node imports are NOT included here to avoid circular imports.
Import nodes directly from graph.nodes or individual agent node files.
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

from .llm_config import (
    MODEL_CONFIG,
    TEMPERATURE_CONFIG,
)

# NOTE: Node imports removed to avoid circular imports
# Import nodes directly when needed:
#   from apps.ai_engine.graph.nodes import supervisor_node, ...
# Or:
#   from apps.ai_engine.agents.core_agent.node import supervisor_node

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
    
    # Config
    "MODEL_CONFIG",
    "TEMPERATURE_CONFIG",
]


# Lazy imports for graph building functions
def build_agent_graph(*args, **kwargs):
    """Lazy import to avoid circular imports."""
    from .graph_builder import build_agent_graph as _build
    return _build(*args, **kwargs)


def create_simple_graph(*args, **kwargs):
    """Lazy import to avoid circular imports."""
    from .graph_builder import create_simple_graph as _create
    return _create(*args, **kwargs)


def run_agent_sync(*args, **kwargs):
    """Lazy import to avoid circular imports."""
    from .graph_builder import run_agent_sync as _run
    return _run(*args, **kwargs)


async def run_agent_async(*args, **kwargs):
    """Lazy import to avoid circular imports."""
    from .graph_builder import run_agent_async as _run
    return await _run(*args, **kwargs)


def get_default_graph(*args, **kwargs):
    """Lazy import to avoid circular imports."""
    from .graph_builder import get_default_graph as _get
    return _get(*args, **kwargs)


def get_graph_mermaid(*args, **kwargs):
    """Lazy import to avoid circular imports."""
    from .graph_builder import get_graph_mermaid as _get
    return _get(*args, **kwargs)

