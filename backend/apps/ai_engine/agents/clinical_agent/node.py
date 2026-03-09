# apps/ai_engine/agents/clinical_agent/node.py
"""
Clinical Agent Node - Bác sĩ chẩn đoán

REFACTORED cho Real Token Streaming:
- Phase 1: LLM stream text thinking (hiển thị realtime)
- Phase 2: Parse text thành structured response
"""

from typing import Dict, Any, List
import re
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_pro, logging_node_execution
from apps.ai_engine.agents.message_utils import convert_and_filter_messages, log_llm_response, extract_final_response
from apps.ai_engine.graph.prompts import get_system_prompt


def extract_thinking_steps(text: str) -> List[str]:
    """Extract thinking steps từ text với format **Bước X:**"""
    steps = []
    pattern = r'\*\*Bước\s*\d+[^*]*\*\*:?\s*([^\*]+?)(?=\*\*Bước|\*\*Kết luận|$)'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    for i, match in enumerate(matches, 1):
        step_text = match.strip()
        if step_text:
            if len(step_text) > 200:
                step_text = step_text[:200] + "..."
            steps.append(f"Bước {i}: {step_text}")
    
    return steps if steps else ["Đã phân tích triệu chứng và đưa ra chẩn đoán"]


def extract_urgency(text: str) -> bool:
    """Check if urgent care is required."""
    urgent_keywords = ["URGENT_HIGH", "cấp cứu ngay", "đe dọa tính mạng", "nguy hiểm"]
    return any(kw.lower() in text.lower() for kw in urgent_keywords)


def extract_diagnosis(text: str) -> List[str]:
    """Extract differential diagnosis từ text."""
    diagnoses = []
    pattern = r'(?:^|\n)\s*\d+\.\s*(.+?)(?:\s*-|\s*\(|$)'
    matches = re.findall(pattern, text, re.MULTILINE)
    for match in matches[:5]:  # Max 5
        match = match.strip()
        if len(match) > 5 and len(match) < 100:
            diagnoses.append(match)
    return diagnoses if diagnoses else []


def clinical_node(state: AgentState) -> Dict[str, Any]:
    """
    Clinical Agent (Bác sĩ chẩn đoán) - Real Token Streaming
    
    Flow:
    1. LLM text thinking
    2. Parse text thành structured response
    """
    logging_node_execution("CLINICAL")
    messages = state["messages"]
    
    # Convert và filter messages
    converted_messages, last_user_message = convert_and_filter_messages(messages, "CLINICAL")
    
    prompt = [SystemMessage(content=get_system_prompt("clinical"))] + converted_messages
    
    try:
        # Direct LLM invoke (text response, không structured output)
        response = llm_pro.invoke(prompt)
        
        # Log response
        text_analysis = log_llm_response(response, "CLINICAL")
        
        # Extract components từ text
        thinking_steps = extract_thinking_steps(text_analysis)
        requires_urgent = extract_urgency(text_analysis)
        diagnoses = extract_diagnosis(text_analysis)
        
        print(f"[CLINICAL] Thinking steps: {len(thinking_steps)}")
        print(f"[CLINICAL] Urgent care: {requires_urgent}")
        print(f"[CLINICAL] Diagnoses found: {len(diagnoses)}")
        
        # Build structured response
        structured_data = {
            "thinking_progress": thinking_steps,
            "final_response": extract_final_response(text_analysis, "Kết luận"),
            "confidence_score": 0.8 if diagnoses else 0.6,
            "differential_diagnosis": diagnoses,
            "requires_urgent_care": requires_urgent,
        }
        
        # Tạo message với structured data
        message = AIMessage(
            content=text_analysis,
            additional_kwargs={
                "agent": "clinical",
                "structured_response": structured_data,
                "thinking_progress": thinking_steps,
                "confidence_score": structured_data["confidence_score"]
            }
        )
        
    except Exception as e:
        print(f"[CLINICAL] Error: {e}")
        message = AIMessage(
            content=f"[Lỗi xử lý] Xin vui lòng mô tả lại triệu chứng của bạn.",
            additional_kwargs={"agent": "clinical", "error": str(e)}
        )
    
    return {
        "messages": [message],
        "current_agent": "clinical"
    }
