"""
Streaming Service Module for AI Engine

Protocol: "Stream Tư Duy - Return Kết Quả" (Stream Thoughts, Return Data)

This module provides SSE streaming infrastructure for LangGraph agents.
The protocol solves the problem of streaming structured JSON to frontend:

1. Thinking Phase: Stream tokens for UI feedback
2. Data Phase: Send complete JSON for component rendering

Usage:
    from apps.ai_engine.streaming import StreamingService, StreamEvent, EventType
    
    service = StreamingService()
    async for event in service.stream_response(message, session_id):
        # event is a dict ready for JSON serialization
        # { "type": "thinking", "content": "..." }  <- Phase 1
        # { "type": "result_json", "content": {...} }  <- Phase 2
        # { "type": "done" }  <- End
        yield f"data: {json.dumps(event)}\n\n"
"""

from .events import (
    StreamEvent,
    EventType,
    StatusType,
    EVENT_MESSAGES_VI,
    TOOL_MESSAGES_VI,
)

from .service import StreamingService


__all__ = [
    # Main service
    "StreamingService",
    
    # Events
    "StreamEvent",
    "EventType",
    "StatusType",
    
    # Vietnamese translations
    "EVENT_MESSAGES_VI",
    "TOOL_MESSAGES_VI",
]
