# apps/ai_engine/agents/paraclinical_agent/node.py
"""
Paraclinical Agent Node - Điều phối viên cận lâm sàng

REFACTORED cho Real Token Streaming:
- Phase 1: LLM với tools cho lab/imaging operations
- Phase 2: Text response để phân tích
"""

from typing import Dict, Any, List
import re
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_paraclinical_with_tools, logging_node_execution
from apps.ai_engine.agents.message_utils import convert_and_filter_messages, log_llm_response, extract_final_response
from .prompts import PARACLINICAL_THINKING_PROMPT


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
    
    return steps if steps else ["Đã xử lý yêu cầu cận lâm sàng"]


def extract_critical_values(text: str) -> List[Dict]:
    """Extract critical values từ text."""
    values = []
    
    # Tìm patterns cho giá trị xét nghiệm
    patterns = [
        r'(\w+)[:\s]+(\d+\.?\d*)\s*(\w+/\w+|\w+)',  # K+: 7.2 mEq/L
        r'(\w+)\s*=\s*(\d+\.?\d*)\s*(\w+/\w+|\w+)',  # K+ = 7.2 mEq/L
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches[:3]:  # Max 3
            test_name, value, unit = match
            status = "NORMAL_VALUE"
            if "CRITICAL" in text.upper() or "NGUY KỊCH" in text.lower():
                if "HIGH" in text.upper() or "cao" in text.lower():
                    status = "CRITICAL_HIGH"
                elif "LOW" in text.upper() or "thấp" in text.lower():
                    status = "CRITICAL_LOW"
            if "PANIC" in text.upper() or "hoảng" in text.lower():
                status = "PANIC_VALUE"
            
            values.append({
                "test_name": test_name,
                "value": value,
                "unit": unit,
                "status": status
            })
    
    return values


def should_trigger_alert(text: str) -> bool:
    """Check if critical alert should be triggered."""
    alert_keywords = ["PANIC_VALUE", "CRITICAL_HIGH", "CRITICAL_LOW", "CẢNH BÁO KHẨN"]
    return any(kw.lower() in text.lower() for kw in alert_keywords)


def paraclinical_node(state: AgentState) -> Dict[str, Any]:
    """
    Paraclinical Agent - Real Token Streaming
    
    Flow:
    1. Nếu cần tools -> return tool calls
    2. LLM text response để phân tích
    """
    logging_node_execution("PARACLINICAL")
    messages = state["messages"]
    
    # Convert và filter messages
    converted_messages, last_user_message = convert_and_filter_messages(messages, "PARACLINICAL")
    
    prompt = [SystemMessage(content=PARACLINICAL_THINKING_PROMPT)] + converted_messages
    
    # Phase 1: Gọi LLM với tools binding
    response = llm_paraclinical_with_tools.invoke(prompt)
    
    # Nếu LLM quyết định gọi tool
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"[PARACLINICAL] Tool calls detected: {[tc['name'] for tc in response.tool_calls]}")
        return {
            "messages": [response],
            "current_agent": "paraclinical"
        }
    
    # Log response
    text_analysis = log_llm_response(response, "PARACLINICAL")
    
    try:
        # Extract components từ text
        thinking_steps = extract_thinking_steps(text_analysis)
        critical_values = extract_critical_values(text_analysis)
        trigger_alert = should_trigger_alert(text_analysis)
        
        print(f"[PARACLINICAL] Thinking steps: {len(thinking_steps)}")
        print(f"[PARACLINICAL] Critical values: {len(critical_values)}")
        print(f"[PARACLINICAL] Trigger alert: {trigger_alert}")
        
        # Build structured data
        structured_data = {
            "thinking_progress": thinking_steps,
            "final_response": extract_final_response(text_analysis, "Kết luận"),
            "confidence_score": 0.9,
            "critical_values": critical_values,
            "trigger_critical_alert": trigger_alert,
        }
        
        message = AIMessage(
            content=text_analysis,
            additional_kwargs={
                "agent": "paraclinical",
                "structured_response": structured_data,
                "thinking_progress": thinking_steps,
            }
        )
        
    except Exception as e:
        print(f"[PARACLINICAL] Error: {e}")
        message = AIMessage(
            content=text_analysis,
            additional_kwargs={"agent": "paraclinical", "error": str(e)}
        )
    
    return {
        "messages": [message],
        "current_agent": "paraclinical"
    }
