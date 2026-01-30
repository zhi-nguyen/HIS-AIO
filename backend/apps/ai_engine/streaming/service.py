"""
Streaming Service for LangGraph Execution

Provides real-time streaming of LangGraph agent responses using astream_events().
Maps internal LangGraph events to frontend-friendly JSON format.
"""

import logging
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from apps.ai_engine.graph.graph_builder import build_agent_graph, get_default_graph
from apps.ai_engine.graph.state import create_initial_state, AgentState
from .events import StreamEvent, EventType, EVENT_MESSAGES_VI, TOOL_MESSAGES_VI

logger = logging.getLogger(__name__)


class StreamingService:
    """
    Service for streaming LangGraph execution events.
    
    Uses LangChain's astream_events() API to provide real-time updates.
    
    Event Mapping:
        - on_chain_start → status(thinking)
        - on_tool_start → tool_start(tool_name)
        - on_tool_end → tool_end(tool_name)
        - on_chat_model_stream → token(content)
        - on_chain_end → done(full_response)
    """
    
    def __init__(self, graph=None):
        """
        Initialize streaming service.
        
        Args:
            graph: Optional compiled LangGraph. Uses default if not provided.
        """
        self._graph = graph
        self._keepalive_interval = 15  # seconds
        self._max_stream_duration = 120  # seconds
    
    @property
    def graph(self):
        """Lazy-load the graph instance."""
        if self._graph is None:
            self._graph = get_default_graph()
        return self._graph
    
    async def stream_response(
        self,
        message: str,
        session_id: str,
        patient_context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream LangGraph execution events.
        
        Args:
            message: User's message (supports Vietnamese UTF-8)
            session_id: Unique session identifier for checkpointing
            patient_context: Optional patient EMR data
            
        Yields:
            Dict events ready for JSON serialization
        """
        logger.info(f"Starting stream: session={session_id}")
        
        # Create initial state
        initial_state = create_initial_state(
            session_id=session_id,
            patient_context=patient_context,
            initial_message=message
        )
        
        # Config for LangGraph with thread_id for checkpointing
        config = {
            "configurable": {
                "thread_id": session_id
            }
        }
        
        # Track state for final response assembly
        full_response_tokens: List[str] = []
        current_agent: Optional[str] = None
        start_time = datetime.now()
        last_event_time = datetime.now()
        
        # Initial thinking status
        yield StreamEvent.status("thinking").to_dict()
        
        try:
            # Use astream_events for real-time streaming
            async for event in self.graph.astream_events(
                initial_state,
                config=config,
                version="v2"
            ):
                event_kind = event.get("event", "")
                event_name = event.get("name", "")
                event_data = event.get("data", {})
                
                # Update last event time for keepalive tracking
                last_event_time = datetime.now()
                
                # Check max duration
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > self._max_stream_duration:
                    logger.warning(f"Stream exceeded max duration: {elapsed}s")
                    yield StreamEvent.error(
                        "Response timeout exceeded",
                        "TIMEOUT_ERROR"
                    ).to_dict()
                    break
                
                # Process different event types
                if event_kind == "on_chain_start":
                    # Agent/chain started
                    chain_name = event_name.lower()
                    if chain_name in EVENT_MESSAGES_VI:
                        current_agent = chain_name
                        yield StreamEvent.status(
                            chain_name,
                            agent=chain_name
                        ).to_dict()
                
                elif event_kind == "on_tool_start":
                    # Tool execution started
                    tool_name = event_name
                    logger.debug(f"Tool started: {tool_name}")
                    yield StreamEvent.tool_start(tool_name).to_dict()
                
                elif event_kind == "on_tool_end":
                    # Tool execution completed
                    tool_name = event_name
                    logger.debug(f"Tool ended: {tool_name}")
                    yield StreamEvent.tool_end(tool_name).to_dict()
                
                elif event_kind == "on_chat_model_stream":
                    # Token-by-token streaming from LLM
                    chunk = event_data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        content = chunk.content
                        full_response_tokens.append(content)
                        yield StreamEvent.token(content).to_dict()
                
                elif event_kind == "on_chain_end":
                    # Check if this is the final output
                    output = event_data.get("output", {})
                    if isinstance(output, dict) and "messages" in output:
                        # Graph completed - extract final response
                        messages = output.get("messages", [])
                        if messages:
                            last_msg = messages[-1]
                            if hasattr(last_msg, "content"):
                                # Use streamed tokens if available, otherwise use final message
                                if full_response_tokens:
                                    full_response = "".join(full_response_tokens)
                                else:
                                    full_response = last_msg.content
                                
                                metadata = {
                                    "agent": current_agent or output.get("current_agent"),
                                    "session_id": session_id,
                                    "duration_seconds": elapsed,
                                }
                                
                                if output.get("triage_code"):
                                    metadata["triage_code"] = output["triage_code"]
                                if output.get("requires_human_intervention"):
                                    metadata["requires_human"] = True
                                
                                yield StreamEvent.done(
                                    full_response,
                                    metadata
                                ).to_dict()
            
            # Ensure we send a done event if we haven't already
            elapsed = (datetime.now() - start_time).total_seconds()
            if full_response_tokens:
                full_response = "".join(full_response_tokens)
                yield StreamEvent.done(
                    full_response,
                    {
                        "session_id": session_id,
                        "duration_seconds": elapsed,
                    }
                ).to_dict()
            
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield StreamEvent.error(str(e), "STREAM_ERROR").to_dict()
    
    async def get_full_response(
        self,
        message: str,
        session_id: str,
        patient_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get complete response without streaming.
        
        Useful for sync endpoints and testing.
        
        Args:
            message: User's message
            session_id: Session identifier
            patient_context: Optional patient data
            
        Returns:
            Dict with response, agent, and metadata
        """
        initial_state = create_initial_state(
            session_id=session_id,
            patient_context=patient_context,
            initial_message=message
        )
        
        config = {
            "configurable": {
                "thread_id": session_id
            }
        }
        
        start_time = datetime.now()
        
        try:
            result = await self.graph.ainvoke(initial_state, config=config)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            messages = result.get("messages", [])
            response_content = ""
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, "content"):
                    response_content = last_msg.content
            
            return {
                "response": response_content,
                "agent": result.get("current_agent"),
                "metadata": {
                    "session_id": session_id,
                    "duration_seconds": elapsed,
                    "triage_code": result.get("triage_code"),
                    "requires_human": result.get("requires_human_intervention", False),
                }
            }
            
        except Exception as e:
            logger.error(f"Full response error: {e}", exc_info=True)
            return {
                "response": "",
                "agent": None,
                "error": str(e),
                "metadata": {
                    "session_id": session_id,
                }
            }
