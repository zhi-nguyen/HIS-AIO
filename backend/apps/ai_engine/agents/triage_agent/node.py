# apps/ai_engine/agents/triage_agent/node.py
"""
Triage Agent Node - Điều dưỡng phân luồng

REFACTORED cho Real Token Streaming:
- Phase 1: LLM với tools cho emergency alerts
- Phase 2: Text response để phân loại
"""

from typing import Dict, Any, List
import re
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_triage_with_tools, logging_node_execution
from apps.ai_engine.agents.message_utils import convert_and_filter_messages, log_llm_response, extract_final_response
from .prompts import TRIAGE_THINKING_PROMPT


def extract_thinking_steps(text: str) -> List[str]:
    """Extract thinking steps từ text."""
    steps = []
    pattern = r'\*\*Bước\s*\d+[^*]*\*\*:?\s*([^\*]+?)(?=\*\*Bước|\*\*Kết luận|$)'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    for i, match in enumerate(matches, 1):
        step_text = match.strip()
        if step_text:
            if len(step_text) > 200:
                step_text = step_text[:200] + "..."
            steps.append(f"Bước {i}: {step_text}")
    
    return steps if steps else ["Đã đánh giá và phân loại bệnh nhân"]


def extract_triage_code(text: str) -> str:
    """Extract triage code từ text."""
    codes = ["CODE_BLUE", "CODE_RED", "CODE_YELLOW", "CODE_GREEN"]
    for code in codes:
        if code in text.upper():
            return code
    return "CODE_GREEN"  # Default


def should_trigger_alert(text: str) -> bool:
    """Check if alert should be triggered."""
    return "CODE_RED" in text.upper() or "CODE_BLUE" in text.upper()


def triage_node(state: AgentState) -> Dict[str, Any]:
    """
    Triage Agent (Điều dưỡng phân luồng) - Real Token Streaming
    
    Flow:
    1. Nếu cần tools (emergency alert) -> return tool calls
    2. LLM text response để phân loại
    """
    logging_node_execution("TRIAGE")
    messages = state["messages"]
    
    # Convert và filter messages
    converted_messages, last_user_message = convert_and_filter_messages(messages, "TRIAGE")
    
    prompt = [SystemMessage(content=TRIAGE_THINKING_PROMPT)] + converted_messages
    
    # Phase 1: Gọi LLM với tools binding
    response = llm_triage_with_tools.invoke(prompt)
    
    # Nếu LLM quyết định gọi tool
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"[TRIAGE] Tool calls detected: {[tc['name'] for tc in response.tool_calls]}")
        return {
            "messages": [response],
            "current_agent": "triage"
        }
    
    # Log response
    text_analysis = log_llm_response(response, "TRIAGE")
    
    try:
        # Extract components từ text
        thinking_steps = extract_thinking_steps(text_analysis)
        triage_code = extract_triage_code(text_analysis)
        trigger_alert = should_trigger_alert(text_analysis)
        
        print(f"[TRIAGE] Thinking steps: {len(thinking_steps)}")
        print(f"[TRIAGE] Triage code: {triage_code}")
        print(f"[TRIAGE] Trigger alert: {trigger_alert}")
        
        # Build structured data
        structured_data = {
            "thinking_progress": thinking_steps,
            "final_response": extract_final_response(text_analysis, "Kết luận phân loại"),
            "confidence_score": 0.9,
            "triage_code": triage_code,
            "trigger_alert": trigger_alert,
        }
        
        message = AIMessage(
            content=text_analysis,
            additional_kwargs={
                "agent": "triage",
                "structured_response": structured_data,
                "thinking_progress": thinking_steps,
                "triage_code": triage_code,
            }
        )
        
    except Exception as e:
        print(f"[TRIAGE] Error: {e}")
        message = AIMessage(
            content=text_analysis,
            additional_kwargs={"agent": "triage", "error": str(e)}
        )
    
    return {
        "messages": [message],
        "current_agent": "triage"
    }
