"""
Agent State Definition for LangGraph

Defines the shared state structure that flows through the agent graph.
Uses TypedDict for type safety and LangGraph compatibility.
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from operator import add


class PatientContext(TypedDict, total=False):
    """Patient-related context data."""
    patient_id: str
    patient_name: str
    emr_data: Dict[str, Any]  # Electronic Medical Record
    vitals: Dict[str, Any]    # Current vital signs
    medical_history: List[Dict[str, Any]]
    current_medications: List[str]
    allergies: List[str]
    lab_results: List[Dict[str, Any]]


class Message(TypedDict, total=False):
    """Individual message in the conversation."""
    role: str       # 'user', 'assistant', 'system', 'tool'
    content: str
    agent: str      # Which agent generated this message
    timestamp: str
    metadata: Dict[str, Any]


class AgentState(TypedDict, total=False):
    """
    Shared state for the Multi-Agent Graph.
    
    This state flows through all nodes in the LangGraph and allows
    agents to communicate and share information.
    
    Attributes:
        messages: Conversation history with role and content
        next_agent: Routing target (set by Supervisor or conditional edges)
        patient_context: EMR, vitals, and other patient data
        tool_outputs: Results from function/tool calls
        error: Error message if something fails
        requires_human_intervention: Flag for escalation to human staff
        confidence_score: Agent's confidence in its response (0.0 - 1.0)
        triage_code: Urgency classification (BLUE, RED, YELLOW, GREEN)
        current_agent: Currently active agent name
        session_id: Unique session identifier for memory management
    """
    # Core conversation state
    messages: Annotated[List[Message], add]
    
    # Routing and control
    next_agent: Optional[str]
    current_agent: Optional[str]
    
    # Patient information
    patient_context: Optional[PatientContext]
    
    # Tool/function call results
    tool_outputs: Dict[str, Any]
    
    # Error handling
    error: Optional[str]
    
    # Human-in-the-loop
    requires_human_intervention: bool
    intervention_reason: Optional[str]
    
    # Agent decision metadata
    confidence_score: Optional[float]
    triage_code: Optional[str]  # BLUE, RED, YELLOW, GREEN
    
    # Session management
    session_id: Optional[str]


# Agent name constants for routing
class AgentName:
    """Constants for agent names used in routing."""
    SUPERVISOR = "supervisor"
    CLINICAL = "clinical"
    TRIAGE = "triage"
    CONSULTANT = "consultant"
    PHARMACIST = "pharmacist"
    SUMMARIZE = "summarize"
    MARKETING = "marketing"
    HUMAN = "human"
    END = "end"


# Triage code constants
class TriageCode:
    """
    Triage urgency codes following standard emergency classification.
    
    - BLUE: Immediate resuscitation needed (cardiac arrest, etc.)
    - RED: Emergency, life-threatening (within 10 minutes)
    - YELLOW: Urgent, not life-threatening (within 60 minutes)
    - GREEN: Non-urgent, stable (can wait)
    """
    BLUE = "CODE_BLUE"
    RED = "CODE_RED"
    YELLOW = "CODE_YELLOW"
    GREEN = "CODE_GREEN"


def create_initial_state(
    session_id: str,
    patient_context: Optional[PatientContext] = None,
    initial_message: Optional[str] = None
) -> AgentState:
    """
    Factory function to create a properly initialized AgentState.
    
    Args:
        session_id: Unique identifier for the conversation session
        patient_context: Optional patient data to include
        initial_message: Optional initial user message
    
    Returns:
        Initialized AgentState ready for graph execution
    
    Example:
        state = create_initial_state(
            session_id="sess-123",
            patient_context={"patient_id": "P001", "patient_name": "Nguyen Van A"},
            initial_message="Tôi bị đau đầu"
        )
    """
    messages: List[Message] = []
    
    if initial_message:
        messages.append({
            "role": "user",
            "content": initial_message,
            "agent": "user",
            "timestamp": "",
            "metadata": {}
        })
    
    return AgentState(
        messages=messages,
        next_agent=AgentName.SUPERVISOR,
        current_agent=None,
        patient_context=patient_context,
        tool_outputs={},
        error=None,
        requires_human_intervention=False,
        intervention_reason=None,
        confidence_score=None,
        triage_code=None,
        session_id=session_id
    )
