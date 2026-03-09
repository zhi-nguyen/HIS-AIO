# apps/ai_engine/agents/summarize_agent/node.py
"""
Summarize Agent Node - Tóm tắt bệnh án

REFACTORED cho Real Token Streaming + Agent-to-Agent Communication:
- LLM text response trực tiếp (không cần tools)
- MỚI: Extract vital_sign_recommendations + triage_hints để truyền cho Triage Agent
"""

from typing import Dict, Any, List, Optional
import re
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_flash, logging_node_execution
from apps.ai_engine.agents.message_utils import convert_and_filter_messages, log_llm_response, extract_final_response
from apps.ai_engine.graph.prompts import get_system_prompt

# Tập hợp các key sinh hiệu hợp lệ
VALID_VITAL_KEYS = {
    "heart_rate", "bp_systolic", "bp_diastolic",
    "respiratory_rate", "temperature", "spo2",
    "weight", "height",
}


def extract_thinking_steps(text: str) -> List[str]:
    """Extract thinking steps từ text."""
    steps = []
    pattern = r'\*\*Bước\s*\d+[^*]*\*\*:?\s*([^\*]+?)(?=\*\*Bước|\*\*Bản Tóm Tắt|$)'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    for i, match in enumerate(matches, 1):
        step_text = match.strip()
        if step_text:
            if len(step_text) > 200:
                step_text = step_text[:200] + "..."
            steps.append(f"Bước {i}: {step_text}")
    
    return steps if steps else ["Đã tóm tắt hồ sơ bệnh án"]


def extract_special_notes(text: str) -> Optional[str]:
    """Extract special notes từ text."""
    if "[QUAN TRỌNG]" in text:
        pattern = r'\[QUAN TRỌNG\][^\n]*'
        matches = re.findall(pattern, text)
        if matches:
            return " | ".join(matches[:3])
    return None


def extract_vital_sign_recommendations(text: str) -> List[str]:
    """
    Extract danh sách chỉ số sinh hiệu được đề xuất từ section
    '**Chỉ số cần ưu tiên đo:**'.
    
    Trả về list các key hợp lệ (VD: ["spo2", "bp_systolic", "heart_rate"]).
    """
    # Tìm section "Chỉ số cần ưu tiên đo:"
    pattern = r'\*\*Ch\u1ec9 s\u1ed1 c\u1ea7n \u01b0u ti\u00ean \u0111o:?\*\*\s*(.+?)(?=\*\*L\u1eddi nh\u1eafc|$)'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    
    if not match:
        # Fallback: tìm theo text ASCII
        pattern2 = r'Ch\u1ec9 s\u1ed1 c\u1ea7n \u01b0u ti\u00ean \u0111o:?\s*(.+?)(?=L\u1eddi nh\u1eafc|$)'
        match = re.search(pattern2, text, re.DOTALL | re.IGNORECASE)
    
    if not match:
        return []
    
    section_text = match.group(1)
    
    # Parse các dòng "- key_name"
    recommendations = []
    for line in section_text.split('\n'):
        line = line.strip().lstrip('-•*').strip().lower()
        # Lọc chỉ lấy các key hợp lệ
        if line in VALID_VITAL_KEYS:
            recommendations.append(line)
        else:
            # Thử match một phần (VD: "spo2 (%)" → "spo2")
            for key in VALID_VITAL_KEYS:
                if key in line:
                    if key not in recommendations:
                        recommendations.append(key)
                    break
    
    return recommendations


def extract_triage_hints(text: str) -> Optional[str]:
    """
    Extract lời nhắc cho Agent Phân Luồng từ section
    '**Lời nhắc cho Agent Phân Luồng:**'.
    """
    pattern = r'\*\*L\u1eddi nh\u1eafc cho Agent Ph\u00e2n Lu\u1ed3ng:?\*\*\s*(.+?)(?=\*\*|$)'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    
    if not match:
        # Fallback
        pattern2 = r'L\u1eddi nh\u1eafc cho Agent Ph\u00e2n Lu\u1ed3ng:?\s*(.+?)(?=\n\n|\*\*|$)'
        match = re.search(pattern2, text, re.DOTALL | re.IGNORECASE)
    
    if not match:
        return None
    
    hint = match.group(1).strip()
    # Giới hạn độ dài hợp lý
    if len(hint) > 500:
        hint = hint[:500] + "..."
    return hint if hint else None


def summarize_node(state: AgentState) -> Dict[str, Any]:
    """
    Summarize Agent - Real Token Streaming

    Flow:
    - LLM text response để tóm tắt hồ sơ
    - Extract vital_sign_recommendations + triage_hints để truyền cho Triage Agent
    """
    logging_node_execution("SUMMARIZE")
    messages = state["messages"]
    
    # Convert và filter messages
    converted_messages, last_user_message = convert_and_filter_messages(messages, "SUMMARIZE")
    
    prompt = [SystemMessage(content=get_system_prompt("summarize"))] + converted_messages
    
    try:
        # Direct LLM invoke (text response)
        response = llm_flash.invoke(prompt)
        
        # Log response
        text_analysis = log_llm_response(response, "SUMMARIZE")
        
        # Extract components từ text
        thinking_steps = extract_thinking_steps(text_analysis)
        special_notes = extract_special_notes(text_analysis)
        vital_recommendations = extract_vital_sign_recommendations(text_analysis)
        triage_hints = extract_triage_hints(text_analysis)
        
        print(f"[SUMMARIZE] Thinking steps: {len(thinking_steps)}")
        print(f"[SUMMARIZE] Vital recommendations: {vital_recommendations}")
        if triage_hints:
            print(f"[SUMMARIZE] Triage hints: {triage_hints[:100]}...")
        if special_notes:
            print(f"[SUMMARIZE] Special notes: {special_notes[:100]}...")
        
        # Build structured data
        structured_data = {
            "thinking_progress": thinking_steps,
            "final_response": extract_final_response(text_analysis, "Bản Tóm Tắt"),
            "confidence_score": 0.85,
            "special_notes": special_notes,
            # MỚI: Agent-to-Agent communication fields
            "vital_sign_recommendations": vital_recommendations,
            "triage_hints": triage_hints,
        }
        
        message = AIMessage(
            content=text_analysis,
            additional_kwargs={
                "agent": "summarize",
                "structured_response": structured_data,
                "thinking_progress": thinking_steps,
                # MỚI: Expose cho downstream
                "vital_sign_recommendations": vital_recommendations,
                "triage_hints": triage_hints,
            }
        )
        
    except Exception as e:
        print(f"[SUMMARIZE] Error: {e}")
        message = AIMessage(
            content=f"[Lỗi xử lý] Không thể tóm tắt hồ sơ. Vui lòng thử lại.",
            additional_kwargs={"agent": "summarize", "error": str(e)}
        )
    
    return {
        "messages": [message],
        "current_agent": "summarize"
    }
