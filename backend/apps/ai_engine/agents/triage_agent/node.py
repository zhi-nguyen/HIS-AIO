# apps/ai_engine/agents/triage_agent/node.py
"""
Triage Agent Node - Điều dưỡng phân luồng

REFACTORED cho Real Token Streaming:
- Phase 1: LLM với tools cho emergency alerts + lookup_department
- Phase 2: Text response để phân loại
- Logic: CODE_RED/BLUE → tự động chỉ định CC (Khoa Cấp Cứu)
"""

from typing import Dict, Any, List, Optional
import re
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage

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


def extract_department_code(text: str) -> str:
    """Extract department code từ text (VD: [NOI_TM], [CC])."""
    matches = re.findall(r'\[([A-Z_]+)\]', text)
    triage_codes = {"CODE_BLUE", "CODE_RED", "CODE_YELLOW", "CODE_GREEN"}
    for match in matches:
        if match not in triage_codes:
            return match
    return ""


def extract_matched_departments(messages: list) -> List[Dict[str, str]]:
    """
    Trích xuất danh sách khoa có độ trùng khớp cao từ tool output.
    
    Duyệt messages tìm ToolMessage từ lookup_department,
    parse kết quả TOP KHOA PHÙ HỢP.
    
    Returns:
        List of {code, name, specialties, score}
    """
    matched = []
    
    for msg in messages:
        # Tìm ToolMessage (output từ lookup_department)
        if isinstance(msg, ToolMessage) and msg.content:
            content = msg.content
            if "TOP KHOA PHÙ HỢP" in content or "Khoa" in content:
                entries = re.findall(
                    r'\d+\.\s*\[(\w+)\]\s*(.+?)\n\s*Chuyên khoa:\s*(.+?)\n\s*Độ phù hợp:\s*(.+?)(?:\n|$)',
                    content
                )
                for code, name, specialties, score in entries:
                    matched.append({
                        "code": code.strip(),
                        "name": name.strip(),
                        "specialties": specialties.strip(),
                        "score": score.strip(),
                    })
        
        if isinstance(msg, AIMessage) and msg.content:
            content = msg.content
            if "TOP KHOA PHÙ HỢP" in content:
                entries = re.findall(
                    r'\d+\.\s*\[(\w+)\]\s*(.+?)\n\s*Chuyên khoa:\s*(.+?)\n\s*Độ phù hợp:\s*(.+?)(?:\n|$)',
                    content
                )
                for code, name, specialties, score in entries:
                    if not any(m["code"] == code.strip() for m in matched):
                        matched.append({
                            "code": code.strip(),
                            "name": name.strip(),
                            "specialties": specialties.strip(),
                            "score": score.strip(),
                        })
    
    return matched


def _check_critical_vitals(text: str) -> Optional[str]:
    """
    Safety net: Quét text tìm chỉ số sinh hiệu và kiểm tra ngưỡng nguy kịch.
    
    Trả về lý do override nếu BẤT KỲ chỉ số nào vượt ngưỡng CODE_RED.
    Trả về None nếu không có chỉ số nào nguy kịch.
    
    Ngưỡng CODE_RED (chỉ cần 1):
    - SpO2 < 92%
    - BP systolic > 180 hoặc < 90
    - HR > 130 hoặc < 45
    - Temp > 40.5 hoặc < 35
    - RR > 28 hoặc < 8
    """
    reasons = []
    
    # SpO2 - CHỈ SỐ QUAN TRỌNG NHẤT
    spo2_matches = re.findall(r'SpO2[:\s]*(\d{1,3})\s*%?', text, re.IGNORECASE)
    if not spo2_matches:
        spo2_matches = re.findall(r'sp[oO]2[:\s]*(\d{1,3})', text)
    for val in spo2_matches:
        v = int(val)
        if v < 92 and v > 0:
            reasons.append(f"SpO2={v}% < 92%")
    
    # Huyết áp tâm thu (systolic)
    bp_patterns = [
        r'BP[-_]?SYS[:\s]*(\d{2,3})',
        r'(?:huyết áp|HA)[:\s]*(\d{2,3})\s*/\s*\d+',
        r'tâm thu[:\s]*(\d{2,3})',
        r'(\d{2,3})\s*/\s*\d+\s*mmHg',
    ]
    for pattern in bp_patterns:
        for val in re.findall(pattern, text, re.IGNORECASE):
            v = int(val)
            if v > 180:
                reasons.append(f"BP_SYS={v} > 180mmHg")
            elif v < 90 and v > 40:
                reasons.append(f"BP_SYS={v} < 90mmHg")
    
    # Nhịp tim
    hr_patterns = [
        r'(?:Tim|HR|nhịp tim|mạch)[:\s]*(\d{2,3})',
        r'(?:Heart Rate)[:\s]*(\d{2,3})',
    ]
    for pattern in hr_patterns:
        for val in re.findall(pattern, text, re.IGNORECASE):
            v = int(val)
            if v > 130:
                reasons.append(f"HR={v} > 130bpm")
            elif v < 45 and v > 0:
                reasons.append(f"HR={v} < 45bpm")
    
    # Nhiệt độ
    temp_patterns = [
        r'(?:nhiệt độ|Temp|T°)[:\s]*(\d{2}(?:\.\d)?)',
        r'(\d{2}\.\d)\s*°?C',
    ]
    for pattern in temp_patterns:
        for val in re.findall(pattern, text, re.IGNORECASE):
            v = float(val)
            if v > 40.5:
                reasons.append(f"Temp={v}°C > 40.5°C")
            elif v < 35 and v > 20:
                reasons.append(f"Temp={v}°C < 35°C")
    
    # Nhịp thở
    rr_patterns = [
        r'(?:RR|nhịp thở)[:\s]*(\d{1,2})\s*/?\s*(?:phút|m|min)?',
    ]
    for pattern in rr_patterns:
        for val in re.findall(pattern, text, re.IGNORECASE):
            v = int(val)
            if v > 28:
                reasons.append(f"RR={v} > 28/min")
            elif v < 8 and v > 0:
                reasons.append(f"RR={v} < 8/min")
    
    return "; ".join(reasons) if reasons else None


def triage_node(state: AgentState) -> Dict[str, Any]:
    """
    Triage Agent (Điều dưỡng phân luồng) - Real Token Streaming
    
    Flow:
    1. Nếu cần tools (emergency alert, lookup_department) -> return tool calls
    2. LLM text response để phân loại
    3. CODE_RED/BLUE -> tự động override department = CC
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
        department_code = extract_department_code(text_analysis)
        
        # ============================================================
        # SAFETY NET: Override CODE nếu chỉ số sinh hiệu vượt ngưỡng
        # Dù LLM nói gì, code-level đảm bảo CODE_RED khi vitals nguy kịch
        # ============================================================
        if triage_code not in ("CODE_RED", "CODE_BLUE"):
            # Tìm user message gốc để kiểm tra vitals
            user_text = ""
            for msg in reversed(messages):
                if hasattr(msg, 'type') and msg.type == 'human':
                    user_text = msg.content if hasattr(msg, 'content') else ""
                    break
                elif isinstance(msg, HumanMessage):
                    user_text = msg.content
                    break
            
            vitals_override = _check_critical_vitals(user_text + " " + text_analysis)
            if vitals_override:
                print(f"[TRIAGE] SAFETY OVERRIDE: {triage_code} → CODE_RED (reason: {vitals_override})")
                triage_code = "CODE_RED"
                trigger_alert = True
        
        # ============================================================
        # LOGIC: CODE_RED/BLUE → Cấp Cứu (CC)
        # Ca nặng luôn chỉ định thẳng khoa Cấp Cứu
        # ============================================================
        if triage_code in ("CODE_RED", "CODE_BLUE"):
            department_code = "CC"
            print(f"[TRIAGE] ⚠ CODE={triage_code} → Override department to CC (Cấp Cứu)")
        
        # ============================================================
        # Extract matched departments từ tool messages  
        # (hỗ trợ Reception xem xét)
        # ============================================================
        matched_departments = extract_matched_departments(messages)
        
        print(f"[TRIAGE] Thinking steps: {len(thinking_steps)}")
        print(f"[TRIAGE] Triage code: {triage_code}")
        print(f"[TRIAGE] Department code: {department_code}")
        print(f"[TRIAGE] Matched departments: {len(matched_departments)}")
        print(f"[TRIAGE] Trigger alert: {trigger_alert}")
        
        # Build structured data
        structured_data = {
            "thinking_progress": thinking_steps,
            "final_response": extract_final_response(text_analysis, "Kết luận phân loại"),
            "confidence_score": 0.9,
            "triage_code": triage_code,
            "department_code": department_code,
            "matched_departments": matched_departments,
            "trigger_alert": trigger_alert,
        }
        
        message = AIMessage(
            content=text_analysis,
            additional_kwargs={
                "agent": "triage",
                "structured_response": structured_data,
                "thinking_progress": thinking_steps,
                "triage_code": triage_code,
                "department_code": department_code,
                "matched_departments": matched_departments,
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
