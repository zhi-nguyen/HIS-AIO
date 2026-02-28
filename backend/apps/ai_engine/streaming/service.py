"""
Streaming Service for LangGraph Execution

Protocol: "Stream Tư Duy - Return Kết Quả" (Stream Thoughts, Return Data)

Giải quyết vấn đề:
- LLM sinh JSON chậm (token by token)
- Nếu chờ JSON xong mới trả về -> UX chậm
- Nếu Stream JSON từng ký tự -> Frontend rất khó parse

Giải pháp:
- Giai đoạn 1 (Thinking): Stream từng token suy luận
- Giai đoạn 2 (Data): Gửi toàn bộ JSON kết quả một lần
"""

import logging
import asyncio
import json
from typing import AsyncGenerator, Dict, Any, Optional, List, Union
from datetime import datetime
from pydantic import BaseModel

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from apps.ai_engine.graph.graph_builder import build_agent_graph, get_default_graph
from apps.ai_engine.graph.state import create_initial_state, AgentState
from .events import StreamEvent, EventType, EVENT_MESSAGES_VI, TOOL_MESSAGES_VI

logger = logging.getLogger(__name__)


class StreamingService:
    """
    Service for streaming LangGraph execution events.
    
    Protocol: "Stream Tư Duy - Return Kết Quả"
    
    Luồng dữ liệu:
        Phase 1 (Thinking Phase): 
          Stream từng token suy luận để bác sĩ thấy AI đang làm việc
          { "type": "thinking", "content": "Đang tra cứu..." }
          
        Phase 2 (Data Phase): 
          Gửi toàn bộ JSON kết quả khi xong
          { "type": "result_json", "content": { ...structured_data... } }
          
        End:
          { "type": "done" }
    
    Event Mapping:
        - on_chain_start → status / tool_start
        - on_chat_model_stream → thinking (token content)
        - on_chain_end → result_json (structured data)
        - final → done
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
    
    def _extract_json_from_thinking(self, thinking_content: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON objects từ thinking content.
        
        Khi LLM output JSON trong thinking stream (thay vì text),
        method này sẽ tìm và parse JSON objects để extract data.
        
        Args:
            thinking_content: Full concatenated thinking content
            
        Returns:
            Dict với data được merge từ tất cả JSON objects tìm thấy
        """
        import re
        
        result = {}
        
        # Pattern để tìm JSON objects (có thể có markdown code blocks)
        # Ưu tiên JSON trong code blocks trước
        code_block_pattern = r'```(?:json)?\s*(\{[^`]*\})\s*```'
        standalone_json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        
        # Tìm trong code blocks trước
        code_blocks = re.findall(code_block_pattern, thinking_content, re.DOTALL)
        for json_str in code_blocks:
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, dict):
                    # Merge vào result, ưu tiên JSON có drug_interactions
                    if parsed.get("drug_interactions"):
                        result = parsed
                        break
                    else:
                        for key, value in parsed.items():
                            if key not in result or (value and not result.get(key)):
                                result[key] = value
            except json.JSONDecodeError:
                continue
        
        # Nếu không có drug_interactions, tìm standalone JSON
        if not result.get("drug_interactions"):
            # Tìm tất cả JSON-like objects
            json_matches = re.findall(standalone_json_pattern, thinking_content)
            for json_str in json_matches:
                try:
                    # Clean up và fix common JSON issues
                    cleaned = json_str.strip()
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, dict):
                        # Merge nếu có drug_interactions
                        if parsed.get("drug_interactions"):
                            for key, value in parsed.items():
                                if value is not None:
                                    result[key] = value
                            break
                except json.JSONDecodeError:
                    continue
        
        # Loại bỏ thinking_progress khỏi result (không cần trong final JSON)
        if "thinking_progress" in result:
            del result["thinking_progress"]
        
        return result if result else None
    
    def _extract_structured_result(
        self, 
        output: Dict[str, Any],
        current_agent: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract structured JSON result from agent output.
        
        Trích xuất dữ liệu có cấu trúc từ response của agent để
        Frontend có thể render cards, alerts, tables.
        
        Args:
            output: Final graph output state
            current_agent: Name of the agent that produced output
            
        Returns:
            Structured dict for frontend rendering, or None
        """
        result = {}
        
        # Basic metadata
        if current_agent:
            result["agent"] = current_agent
            
        # Triage information
        if output.get("triage_code"):
            result["triage_code"] = output["triage_code"]
            result["status"] = "urgent" if output["triage_code"] in ["CODE_BLUE", "CODE_RED"] else "normal"
            
        # Human intervention needed
        if output.get("requires_human_intervention"):
            result["requires_human"] = True
            result["intervention_reason"] = output.get("intervention_reason", "")
            
        # Tool outputs (drug interactions, lab results, etc.)
        tool_outputs = output.get("tool_outputs", {})
        if tool_outputs:
            # Drug interactions
            if "drug_interactions" in tool_outputs:
                result["drug_interactions"] = tool_outputs["drug_interactions"]
                
            # Lab results / critical values
            if "lab_results" in tool_outputs:
                result["lab_results"] = tool_outputs["lab_results"]
                
            # ICD-10 codes
            if "icd10_codes" in tool_outputs:
                result["icd10_codes"] = tool_outputs["icd10_codes"]
                
            # Any other tool output
            for key, value in tool_outputs.items():
                if key not in result:
                    result[key] = value
        
        # Extract structured data from last message
        messages = output.get("messages", [])
        if messages:
            last_msg = messages[-1]
            
            # PRIORITY 1: Check for structured_response in additional_kwargs
            # This is where format_structured_response_to_message puts the data
            if hasattr(last_msg, "additional_kwargs") and last_msg.additional_kwargs:
                kwargs = last_msg.additional_kwargs
                
                # Get full structured response (contains all fields from Pydantic model)
                if "structured_response" in kwargs and kwargs["structured_response"]:
                    structured_data = kwargs["structured_response"]
                    
                    # Merge all structured data into result
                    # This includes: drug_interactions, alternative_drugs, dosage_guidance, etc.
                    for key, value in structured_data.items():
                        if key not in ["thinking_progress"] and value is not None:
                            result[key] = value
                
                # Also check for older key name (backwards compatibility)
                elif "structured_output" in kwargs and kwargs["structured_output"]:
                    result.update(kwargs["structured_output"])
            
            # PRIORITY 2: If content is JSON string, try to parse
            if hasattr(last_msg, "content"):
                content = last_msg.content
                
                # Try to parse JSON if it's a string (and we don't already have message)
                if isinstance(content, str) and "message" not in result:
                    try:
                        parsed = json.loads(content)
                        if isinstance(parsed, dict):
                            # Merge but don't overwrite existing keys
                            for key, value in parsed.items():
                                if key not in result and value is not None:
                                    result[key] = value
                    except (json.JSONDecodeError, TypeError):
                        # Plain text response, add as message if not already set
                        if "message" not in result and "final_response" not in result:
                            result["message"] = content
                        
                # If already a dict, merge it
                elif isinstance(content, dict):
                    for key, value in content.items():
                        if key not in result and value is not None:
                            result[key] = value
        
        # Ensure we have a message field for frontend
        if "message" not in result:
            if "final_response" in result:
                result["message"] = result["final_response"]
        
        # ==========================================
        # Check for UI Action embedded by consultant node
        # (fallback nếu on_tool_end interception bị miss)
        # ==========================================
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "additional_kwargs") and last_msg.additional_kwargs:
                ui_action = last_msg.additional_kwargs.get("__ui_action__")
                if ui_action and isinstance(ui_action, dict):
                    result["__ui_action__"] = ui_action
                    logger.info(f"[FALLBACK] UI Action found in additional_kwargs: {ui_action.get('__ui_action__', 'unknown')}")
        
        return result if result else None
    
    async def stream_response(
        self,
        message: str,
        session_id: str,
        patient_context: Optional[Dict[str, Any]] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream LangGraph execution with "Stream Tư Duy - Return Kết Quả" protocol.
        
        Args:
            message: User's message (supports Vietnamese UTF-8)
            session_id: Unique session identifier for checkpointing
            patient_context: Optional patient EMR data
            user_context: Optional user auth context for RBAC enforcement
            
        Yields:
            Dict events in the format:
                Phase 1: { "type": "thinking", "content": "..." }
                Phase 2: { "type": "result_json", "content": {...} }
                End: { "type": "done" }
        """
        logger.info(f"Starting stream: session={session_id}")
        
        # Create initial state
        initial_state = create_initial_state(
            session_id=session_id,
            patient_context=patient_context,
            initial_message=message,
            user_context=user_context
        )
        
        # Config for LangGraph with thread_id for checkpointing
        config = {
            "configurable": {
                "thread_id": session_id
            }
        }
        
        # Track state for final response assembly
        thinking_tokens: List[str] = []
        current_agent: Optional[str] = None
        start_time = datetime.now()
        result_sent = False
        final_output: Optional[Dict[str, Any]] = None
        
        # Initial status
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
                
                # Check max duration
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > self._max_stream_duration:
                    logger.warning(f"Stream exceeded max duration: {elapsed}s")
                    yield StreamEvent.error(
                        "Response timeout exceeded",
                        "TIMEOUT_ERROR"
                    ).to_dict()
                    break
                
                # =========================================================
                # PROCESS EVENTS
                # =========================================================
                
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
                    tool_output = event_data.get("output", "")
                    logger.debug(f"Tool ended: {tool_name}")
                    
                    # Check if tool output contains a UI action signal
                    # (e.g., open_booking_form returns JSON with __ui_action__)
                    try:
                        output_str = str(tool_output.content) if hasattr(tool_output, 'content') else str(tool_output)
                        parsed_output = json.loads(output_str)
                        if isinstance(parsed_output, dict) and parsed_output.get("__ui_action__"):
                            action_name = parsed_output.pop("__ui_action__")
                            logger.info(f"UI Action intercepted: {action_name}")
                            yield StreamEvent.ui_action(action_name, parsed_output).to_dict()
                            # Don't yield normal tool_end for UI actions
                            continue
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass
                    
                    yield StreamEvent.tool_end(tool_name).to_dict()
                
                elif event_kind == "on_chat_model_stream":
                    # =========================================
                    # PHASE 1: THINKING (Token-by-token)
                    # =========================================
                    chunk = event_data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        content = chunk.content
                        thinking_tokens.append(content)
                        # Stream thinking token
                        yield StreamEvent.thinking(content).to_dict()
                
                elif event_kind == "on_chain_end":
                    # Check if this is the final output
                    output = event_data.get("output", {})
                    
                    # DEBUG: Log chain end events
                    if isinstance(output, dict):
                        has_messages = "messages" in output
                        msg_count = len(output.get("messages", []))
                        agent = output.get("current_agent", "unknown")
                        logger.info(f"[DEBUG] on_chain_end: name={event_name}, agent={agent}, has_messages={has_messages}, msg_count={msg_count}")
                        
                        if has_messages and msg_count > 0:
                            last_msg = output["messages"][-1]
                            if hasattr(last_msg, "content"):
                                content_preview = str(last_msg.content)[:100] if last_msg.content else "(empty)"
                                logger.info(f"[DEBUG] Last message content preview: {content_preview}")
                            if hasattr(last_msg, "additional_kwargs"):
                                has_structured = "structured_response" in last_msg.additional_kwargs
                                logger.info(f"[DEBUG] Has structured_response: {has_structured}")
                    
                    if isinstance(output, dict) and "messages" in output:
                        final_output = output
            
            # =========================================================
            # PHASE 2: RESULT_JSON (After all processing complete)
            # =========================================================
            if final_output and not result_sent:
                elapsed = (datetime.now() - start_time).total_seconds()
                
                # Extract structured result
                structured_result = self._extract_structured_result(
                    final_output, 
                    current_agent
                )
                
                # FALLBACK: Nếu không extract được đủ data từ message,
                # thử parse JSON từ thinking content (vì LLM có thể output JSON trong thinking)
                if structured_result and not structured_result.get("drug_interactions"):
                    full_thinking = "".join(thinking_tokens)
                    parsed_from_thinking = self._extract_json_from_thinking(full_thinking)
                    if parsed_from_thinking:
                        # Merge data từ thinking vào result (không overwrite existing)
                        for key, value in parsed_from_thinking.items():
                            if key not in structured_result and value is not None:
                                structured_result[key] = value
                            elif key == "drug_interactions" and value:
                                structured_result[key] = value
                            elif key == "final_response" and value and "Đang kiểm tra" not in str(value):
                                structured_result["message"] = value
                                structured_result["final_response"] = value
                
                # Add metadata
                if structured_result:
                    structured_result["metadata"] = {
                        "session_id": session_id,
                        "duration_seconds": round(elapsed, 2),
                        "agent": current_agent,
                    }
                    
                    # ==========================================
                    # FALLBACK: Emit ui_action BEFORE result_json
                    # nếu consultant node gắn __ui_action__ data
                    # ==========================================
                    ui_action_data = structured_result.pop("__ui_action__", None)
                    if ui_action_data and isinstance(ui_action_data, dict):
                        action_name = ui_action_data.pop("__ui_action__", "unknown")
                        logger.info(f"[STREAM] Emitting fallback ui_action: {action_name}")
                        yield StreamEvent.ui_action(action_name, ui_action_data).to_dict()
                    
                    # Send the complete JSON result
                    yield StreamEvent.result_json(structured_result).to_dict()
                    result_sent = True
                else:
                    # Fallback: try to parse thinking as result
                    full_response = "".join(thinking_tokens)
                    parsed_result = self._extract_json_from_thinking(full_response)
                    
                    if parsed_result:
                        parsed_result["agent"] = current_agent
                        parsed_result["metadata"] = {
                            "session_id": session_id,
                            "duration_seconds": round(elapsed, 2),
                            "agent": current_agent,
                        }
                        yield StreamEvent.result_json(parsed_result).to_dict()
                    else:
                        yield StreamEvent.result_json({
                            "message": full_response,
                            "metadata": {
                                "session_id": session_id,
                                "duration_seconds": round(elapsed, 2),
                                "agent": current_agent,
                            }
                        }).to_dict()
                    result_sent = True
            
            # =========================================================
            # DONE EVENT
            # =========================================================
            yield StreamEvent.done().to_dict()
            
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield StreamEvent.error(str(e), "STREAM_ERROR").to_dict()
            yield StreamEvent.done().to_dict()
    
    async def get_full_response(
        self,
        message: str,
        session_id: str,
        patient_context: Optional[Dict[str, Any]] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get complete response without streaming.
        
        Returns the same format as stream_response's result_json event.
        Useful for sync endpoints and testing.
        
        Args:
            message: User's message
            session_id: Session identifier
            patient_context: Optional patient data
            user_context: Optional user auth context for RBAC
            
        Returns:
            Dict in result_json format with structured data
        """
        initial_state = create_initial_state(
            session_id=session_id,
            patient_context=patient_context,
            initial_message=message,
            user_context=user_context
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
            current_agent = result.get("current_agent")
            
            # Use the same structured extraction as streaming
            structured_result = self._extract_structured_result(result, current_agent)
            
            if structured_result is None:
                # Fallback to basic response format
                messages = result.get("messages", [])
                response_content = ""
                if messages:
                    last_msg = messages[-1]
                    if hasattr(last_msg, "content"):
                        response_content = last_msg.content
                
                structured_result = {"message": response_content}
            
            # Add metadata
            structured_result["metadata"] = {
                "session_id": session_id,
                "duration_seconds": round(elapsed, 2),
                "agent": current_agent,
                "triage_code": result.get("triage_code"),
                "requires_human": result.get("requires_human_intervention", False),
            }
            
            return structured_result
            
        except Exception as e:
            logger.error(f"Full response error: {e}", exc_info=True)
            return {
                "error": str(e),
                "metadata": {
                    "session_id": session_id,
                }
            }

