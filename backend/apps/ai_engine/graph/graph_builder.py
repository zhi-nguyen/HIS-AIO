"""
LangGraph Builder for Multi-Agent Medical System

Compiles the agent graph with:
- Conditional routing from Supervisor
- Human-in-the-loop edges
- State management
"""

import logging
from typing import Optional, Dict, Any, Literal

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState, AgentName, create_initial_state
from .nodes import (
    supervisor_node,
    clinical_node_with_escalation,
    triage_node_with_escalation,
    consultant_node,
    pharmacist_node,
    paraclinical_node,
    summarize_node,
    marketing_node,
    human_intervention_node,
    end_node,
    NODE_REGISTRY,
    consultant_tools,
    pharmacist_tools,
    triage_tools,
    paraclinical_tools,
)
from langgraph.prebuilt import ToolNode, tools_condition

logger = logging.getLogger(__name__)


# =============================================================================
# ROUTING FUNCTIONS
# =============================================================================

def route_from_supervisor(state: AgentState) -> str:
    """
    Conditional edge function to route from Supervisor to specialist agents.
    
    Args:
        state: Current AgentState after supervisor processing
    
    Returns:
        Name of the next node to execute
    """
    next_agent = state.get("next_agent", AgentName.CONSULTANT)
    
    # Map agent names to node names
    valid_agents = {
        AgentName.CLINICAL,
        AgentName.TRIAGE,
        AgentName.CONSULTANT,
        AgentName.PHARMACIST,
        AgentName.PARACLINICAL,
        AgentName.SUMMARIZE,
        AgentName.MARKETING,
        AgentName.HUMAN,
        AgentName.END,
    }
    
    if next_agent in valid_agents:
        logger.info(f"Routing to: {next_agent}")
        return next_agent
    
    # Default fallback
    logger.warning(f"Unknown next_agent '{next_agent}', defaulting to consultant")
    return AgentName.CONSULTANT


def check_human_intervention(state: AgentState) -> str:
    """
    Check if human intervention is required after clinical/triage processing.
    
    Args:
        state: Current AgentState
    
    Returns:
        'human' if intervention required, 'end' otherwise
    """
    if state.get("requires_human_intervention", False):
        return AgentName.HUMAN
    return AgentName.END


def should_continue(state: AgentState) -> str:
    """
    Determine if conversation should continue or end.
    
    Used after specialist agents finish to either:
    - Route back to supervisor for follow-up
    - End the conversation
    """
    # Check for explicit end conditions
    if state.get("next_agent") == AgentName.END:
        return AgentName.END
    
    if state.get("requires_human_intervention"):
        return AgentName.HUMAN
    
    # Check if there's an error that should stop processing
    if state.get("error"):
        logger.warning(f"Error detected: {state.get('error')}")
        return AgentName.END
    
    # Default: end after specialist response
    # In a more interactive system, could route back to supervisor
    return AgentName.END


# =============================================================================
# PERSISTENCE SETUP
# =============================================================================

def get_db_connection_pool():
    """
    Create a connection pool for PostgresSaver.
    """
    try:
        from django.conf import settings
        from psycopg_pool import ConnectionPool
        
        db_config = settings.DATABASES['default']
        # Construct simplified connection string or use params
        # conninfo format: postgresql://user:password@host:port/dbname
        conninfo = f"postgresql://{db_config['USER']}:{db_config['PASSWORD']}@{db_config['HOST']}:{db_config['PORT']}/{db_config['NAME']}"
        
        pool = ConnectionPool(
            conninfo=conninfo,
            max_size=20,
            kwargs={"autocommit": True}
        )
        return pool
    except ImportError:
        logger.warning("psycopg_pool not installed. Persistence will use MemorySaver.")
        return None
    except Exception as e:
        logger.warning(f"Could not create DB pool: {e}. Persistence will use MemorySaver.")
        return None

# =============================================================================
# GRAPH BUILDER
# =============================================================================

def build_agent_graph(
    checkpointer: Optional[Any] = None,
    include_memory: bool = True
) -> StateGraph:
    """
    Build and compile the Multi-Agent LangGraph.
    
    Args:
        checkpointer: Optional LangGraph checkpointer for persistence
        include_memory: If True and no checkpointer provided, attempt to use PostgresSaver, fallback to MemorySaver
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph builder
    builder = StateGraph(AgentState)
    
    # =========================================================================
    # ADD NODES
    # =========================================================================
    
    # Supervisor (entry point for routing)
    builder.add_node(AgentName.SUPERVISOR, supervisor_node)
    
    # Specialist agents
    builder.add_node(AgentName.CLINICAL, clinical_node_with_escalation)
    builder.add_node(AgentName.TRIAGE, triage_node_with_escalation)
    builder.add_node(AgentName.CONSULTANT, consultant_node)
    builder.add_node(AgentName.PHARMACIST, pharmacist_node)
    builder.add_node(AgentName.PARACLINICAL, paraclinical_node)
    builder.add_node(AgentName.SUMMARIZE, summarize_node)
    builder.add_node(AgentName.MARKETING, marketing_node)

    # Tool Nodes
    builder.add_node("consultant_tools", ToolNode(consultant_tools))
    builder.add_node("pharmacist_tools", ToolNode(pharmacist_tools))
    builder.add_node("triage_tools", ToolNode(triage_tools))
    builder.add_node("paraclinical_tools", ToolNode(paraclinical_tools))
    
    # Human-in-the-loop and termination
    builder.add_node(AgentName.HUMAN, human_intervention_node)
    builder.add_node(AgentName.END, end_node)
    
    # =========================================================================
    # ADD EDGES
    # =========================================================================
    
    # Entry point: START -> Supervisor
    builder.add_edge(START, AgentName.SUPERVISOR)
    
    # Conditional routing from Supervisor
    builder.add_conditional_edges(
        AgentName.SUPERVISOR,
        route_from_supervisor,
        {
            AgentName.CLINICAL: AgentName.CLINICAL,
            AgentName.TRIAGE: AgentName.TRIAGE,
            AgentName.CONSULTANT: AgentName.CONSULTANT,
            AgentName.PHARMACIST: AgentName.PHARMACIST,
            AgentName.PARACLINICAL: AgentName.PARACLINICAL,
            AgentName.SUMMARIZE: AgentName.SUMMARIZE,
            AgentName.MARKETING: AgentName.MARKETING,
            AgentName.HUMAN: AgentName.HUMAN,
            AgentName.END: AgentName.END,
        }
    )
    
    # After Clinical: check for human intervention
    builder.add_conditional_edges(
        AgentName.CLINICAL,
        check_human_intervention,
        {
            AgentName.HUMAN: AgentName.HUMAN,
            AgentName.END: AgentName.END,
        }
    )
    
    # Consultant flow: Consultant -> Tools? -> Consultant -> End
    builder.add_conditional_edges(
        AgentName.CONSULTANT,
        tools_condition,
        {"tools": "consultant_tools", END: AgentName.END}
    )
    builder.add_edge("consultant_tools", AgentName.CONSULTANT)

    # Pharmacist flow
    builder.add_conditional_edges(
        AgentName.PHARMACIST,
        tools_condition,
        {"tools": "pharmacist_tools", END: AgentName.END}
    )
    builder.add_edge("pharmacist_tools", AgentName.PHARMACIST)

    # Paraclinical flow: Paraclinical -> Tools? -> Paraclinical -> End
    builder.add_conditional_edges(
        AgentName.PARACLINICAL,
        tools_condition,
        {"tools": "paraclinical_tools", END: AgentName.END}
    )
    builder.add_edge("paraclinical_tools", AgentName.PARACLINICAL)

    # Triage flow: Triage -> Tools? -> Triage -> Human Check? -> End
    def triage_routing(state):
        # 1. Check for tool calls
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        # 2. Check for human intervention
        return check_human_intervention(state)

    builder.add_conditional_edges(
        AgentName.TRIAGE,
        triage_routing,
        {
            "tools": "triage_tools",
            AgentName.HUMAN: AgentName.HUMAN,
            AgentName.END: AgentName.END
        }
    )
    
    builder.add_edge(AgentName.SUMMARIZE, AgentName.END)
    builder.add_edge(AgentName.MARKETING, AgentName.END)
    
    # Human intervention -> End
    builder.add_edge(AgentName.HUMAN, AgentName.END)
    
    # End node is terminal
    builder.add_edge(AgentName.END, END)
    
    # =========================================================================
    # COMPILE GRAPH
    # =========================================================================
    
    # Setup checkpointer for persistence
    if checkpointer is None and include_memory:
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            pool = get_db_connection_pool()
            if pool:
                checkpointer = PostgresSaver(pool)
                checkpointer.setup() # Ensure tables exist
                logger.info("Using PostgresSaver for persistence")
            else:
                checkpointer = MemorySaver()
                logger.info("Using MemorySaver (Postgres pool failed)")
        except ImportError:
            checkpointer = MemorySaver()
            logger.info("Using MemorySaver (PostgresSaver import failed)")
    
    # Compile
    graph = builder.compile(checkpointer=checkpointer)
    
    logger.info("Agent graph compiled successfully")
    
    return graph


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_simple_graph() -> StateGraph:
    """
    Create a simple graph without persistence (for testing).
    
    Returns:
        Compiled StateGraph without checkpointer
    """
    return build_agent_graph(include_memory=False)


async def run_agent_async(
    graph: StateGraph,
    message: str,
    session_id: str,
    patient_context: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None
) -> AgentState:
    """
    Run the agent graph asynchronously.
    
    Args:
        graph: Compiled LangGraph
        message: User message
        session_id: Session identifier
        patient_context: Optional patient data
        config: Optional LangGraph config (e.g., for thread_id)
    
    Returns:
        Final AgentState after graph execution
    
    Example:
        graph = build_agent_graph()
        result = await run_agent_async(
            graph,
            message="Tôi bị đau bụng",
            session_id="sess-123",
            patient_context={"patient_name": "Nguyen Van A"}
        )
        print(result["messages"][-1]["content"])
    """
    initial_state = create_initial_state(
        session_id=session_id,
        patient_context=patient_context,
        initial_message=message
    )
    
    # Default config with thread_id for checkpointing
    if config is None:
        config = {"configurable": {"thread_id": session_id}}
    
    # Run the graph
    result = await graph.ainvoke(initial_state, config)
    
    return result


def run_agent_sync(
    graph: StateGraph,
    message: str,
    session_id: str,
    patient_context: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None
) -> AgentState:
    """
    Run the agent graph synchronously.
    
    Same as run_agent_async but for synchronous execution.
    """
    initial_state = create_initial_state(
        session_id=session_id,
        patient_context=patient_context,
        initial_message=message
    )
    
    if config is None:
        config = {"configurable": {"thread_id": session_id}}
    
    result = graph.invoke(initial_state, config)
    
    return result


# =============================================================================
# GRAPH VISUALIZATION (Optional)
# =============================================================================

def get_graph_mermaid(graph: StateGraph) -> str:
    """
    Generate Mermaid diagram of the graph.
    
    Args:
        graph: Compiled StateGraph
    
    Returns:
        Mermaid diagram string
    
    Example:
        graph = build_agent_graph()
        mermaid = get_graph_mermaid(graph)
        print(mermaid)
    """
    try:
        return graph.get_graph().draw_mermaid()
    except Exception as e:
        logger.warning(f"Could not generate Mermaid diagram: {e}")
        return ""


# =============================================================================
# DEFAULT GRAPH INSTANCE
# =============================================================================

# Create a default graph instance for convenience
_default_graph = None


def get_default_graph() -> StateGraph:
    """
    Get or create the default graph instance.
    
    Uses lazy initialization to avoid loading at import time.
    
    Returns:
        Default compiled StateGraph
    """
    global _default_graph
    if _default_graph is None:
        _default_graph = build_agent_graph()
    return _default_graph
