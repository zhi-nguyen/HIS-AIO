"""
API Views for Streaming LangGraph Responses

Provides Server-Sent Events (SSE) endpoint for real-time AI response streaming.
Supports Vietnamese characters (UTF-8) for medical context.
"""

import json
import logging
import asyncio
from functools import wraps
from typing import AsyncGenerator, Dict, Any, Optional

from django.http import StreamingHttpResponse, JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.ai_engine.streaming.service import StreamingService
from apps.ai_engine.streaming.events import StreamEvent, EventType
from apps.ai_engine.agents.security import extract_user_context

logger = logging.getLogger(__name__)


def async_view(view_func):
    """Decorator to handle async views in Django."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        return asyncio.run(view_func(request, *args, **kwargs))
    return wrapper


async def generate_sse_events(
    message: str,
    session_id: str,
    patient_context: Optional[Dict[str, Any]] = None,
    user_context: Optional[Dict[str, Any]] = None
) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE-formatted events from LangGraph streaming.
    
    Args:
        message: User's message in Vietnamese
        session_id: Unique session identifier
        patient_context: Optional patient EMR data
        user_context: Optional user auth context for RBAC
        
    Yields:
        SSE-formatted strings: "data: {json}\n\n"
    """
    streaming_service = StreamingService()
    
    try:
        async for event in streaming_service.stream_response(
            message=message,
            session_id=session_id,
            patient_context=patient_context,
            user_context=user_context
        ):
            # Format as SSE: data: {json}\n\n
            # ensure_ascii=False to preserve Vietnamese characters
            sse_data = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield sse_data
            
    except Exception as e:
        logger.error(f"Streaming error: {e}", exc_info=True)
        error_event = {
            "type": EventType.ERROR,
            "message": str(e),
            "code": "STREAM_ERROR"
        }
        yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"


def sync_sse_generator(async_gen):
    """
    Convert async generator to sync generator for Django StreamingHttpResponse.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        agen = async_gen.__aiter__()
        while True:
            try:
                yield loop.run_until_complete(agen.__anext__())
            except StopAsyncIteration:
                break
    finally:
        loop.close()


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def chat_stream(request: HttpRequest) -> StreamingHttpResponse:
    """
    SSE endpoint for streaming LangGraph responses.
    
    Request Body (JSON):
        {
            "message": "Tôi bị đau đầu",  # User message (Vietnamese)
            "session_id": "sess-123",      # Session identifier
            "patient_context": {...}       # Optional patient data
        }
    
    Response (SSE Stream):
        Content-Type: text/event-stream
        
        data: {"type": "status", "status": "thinking", "message": "Đang suy nghĩ..."}
        data: {"type": "status", "status": "tool", "message": "Đang tra cứu dược thư..."}
        data: {"type": "token", "content": "Xin"}
        data: {"type": "token", "content": " chào"}
        data: {"type": "done", "full_response": "...", "metadata": {...}}
    
    CORS Headers:
        Includes headers for cross-origin streaming support.
    """
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    try:
        # Parse request body
        body = json.loads(request.body.decode('utf-8'))
        message = body.get("message", "")
        session_id = body.get("session_id", "default-session")
        patient_context = body.get("patient_context")
        
        if not message:
            return JsonResponse(
                {"error": "Message is required", "code": "MISSING_MESSAGE"},
                status=400
            )
        
        logger.info(f"SSE stream request: session={session_id}, message_len={len(message)}")
        
        # Extract user context from JWT (if authenticated) or default to ANONYMOUS
        user_context = extract_user_context(request)
        
        # Create async generator
        async_gen = generate_sse_events(message, session_id, patient_context, user_context)
        
        # Create streaming response
        response = StreamingHttpResponse(
            sync_sse_generator(async_gen),
            content_type="text/event-stream; charset=utf-8"
        )
        
        # SSE and CORS headers
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"  # Disable nginx buffering
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        
        return response
        
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in request: {e}")
        return JsonResponse(
            {"error": "Invalid JSON", "code": "INVALID_JSON"},
            status=400
        )
    except Exception as e:
        logger.error(f"Chat stream error: {e}", exc_info=True)
        return JsonResponse(
            {"error": str(e), "code": "INTERNAL_ERROR"},
            status=500
        )


@csrf_exempt
@require_http_methods(["POST"])
def chat_sync(request: HttpRequest) -> JsonResponse:
    """
    Synchronous chat endpoint for non-streaming requests.
    
    Useful for:
    - Testing without SSE
    - Clients that don't support SSE
    - Simple integrations
    
    Request Body (JSON):
        {
            "message": "Tôi bị đau đầu",
            "session_id": "sess-123",
            "patient_context": {...}
        }
    
    Response (JSON):
        {
            "response": "...",
            "agent": "consultant",
            "metadata": {...}
        }
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
        message = body.get("message", "")
        session_id = body.get("session_id", "default-session")
        patient_context = body.get("patient_context")
        
        if not message:
            return JsonResponse(
                {"error": "Message is required", "code": "MISSING_MESSAGE"},
                status=400
            )
        
        streaming_service = StreamingService()
        
        # Extract user context from JWT (if authenticated) or default to ANONYMOUS
        user_context = extract_user_context(request)
        
        result = asyncio.run(streaming_service.get_full_response(
            message=message,
            session_id=session_id,
            patient_context=patient_context,
            user_context=user_context
        ))
        
        response = JsonResponse(result, json_dumps_params={'ensure_ascii': False})
        response["Access-Control-Allow-Origin"] = "*"
        return response
        
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON", "code": "INVALID_JSON"},
            status=400
        )
    except Exception as e:
        logger.error(f"Chat sync error: {e}", exc_info=True)
        return JsonResponse(
            {"error": str(e), "code": "INTERNAL_ERROR"},
            status=500
        )


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request: HttpRequest) -> JsonResponse:
    """
    Health check endpoint for the AI API.
    
    Returns:
        {"status": "ok", "service": "ai-streaming"}
    """
    return JsonResponse({
        "status": "ok",
        "service": "ai-streaming",
        "version": "1.0.0"
    })
