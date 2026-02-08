# apps/ai_engine/agents/pharmacist_agent/node.py
"""
Pharmacist Agent Node - Dược sĩ lâm sàng

REFACTORED cho Real Token Streaming:
- Phase 1: LLM stream text thinking (hiển thị realtime)
- Phase 2: Format thành structured JSON response
"""

from typing import Dict, Any, List, Optional
import json
import re
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import (
    llm_pharmacist_with_tools, 
    llm_flash, 
    logging_node_execution
)
from apps.ai_engine.agents.schemas import PharmacistResponse, DrugInteraction
from apps.ai_engine.agents.utils import format_structured_response_to_message
from apps.ai_engine.agents.message_utils import extract_final_response
from .prompts import PHARMACIST_THINKING_PROMPT, PHARMACIST_STRUCTURE_PROMPT


def parse_severity(text: str) -> str:
    """Extract severity level từ text."""
    text_upper = text.upper()
    if "MAJOR" in text_upper or "NGHIÊM TRỌNG" in text_upper:
        return "SEVERITY_MAJOR"
    elif "MODERATE" in text_upper or "TRUNG BÌNH" in text_upper:
        return "SEVERITY_MODERATE"
    elif "MINOR" in text_upper or "NHẸ" in text_upper:
        return "SEVERITY_MINOR"
    return "SEVERITY_MODERATE"  # Default


def extract_drug_interactions_from_text(text: str) -> List[Dict[str, str]]:
    """
    Extract drug interactions từ text analysis.
    
    Tìm patterns như:
    - "Warfarin + Ibuprofen: [SEVERITY_MAJOR]"
    - "Thuốc A và Thuốc B có tương tác nghiêm trọng"
    """
    interactions = []
    lines = text.split('\n')
    
    current_pair = None
    current_severity = None
    current_desc = []
    current_rec = []
    
    for line in lines:
        line = line.strip()
        
        # Tìm drug pair với severity
        severity_match = re.search(r'\[SEVERITY_(MAJOR|MODERATE|MINOR)\]', line, re.IGNORECASE)
        
        # Tìm cặp thuốc
        pair_patterns = [
            r'(\w+)\s*\+\s*(\w+)',  # Warfarin + Ibuprofen
            r'(\w+)\s+và\s+(\w+)',   # Warfarin và Ibuprofen
        ]
        
        for pattern in pair_patterns:
            pair_match = re.search(pattern, line, re.IGNORECASE)
            if pair_match:
                # Save previous interaction
                if current_pair and current_severity:
                    interactions.append({
                        "drug_pair": current_pair,
                        "severity": current_severity,
                        "description": " ".join(current_desc) if current_desc else "Có tương tác thuốc",
                        "recommendation": " ".join(current_rec) if current_rec else "Cần theo dõi"
                    })
                
                drug1, drug2 = pair_match.groups()
                current_pair = f"{drug1} + {drug2}"
                current_severity = f"SEVERITY_{severity_match.group(1).upper()}" if severity_match else None
                current_desc = []
                current_rec = []
                break
        
        # Collect descriptions
        if current_pair:
            if severity_match and not current_severity:
                current_severity = f"SEVERITY_{severity_match.group(1).upper()}"
            
            # Look for recommendations
            if any(kw in line.lower() for kw in ["khuyến", "đề xuất", "thay thế", "nên", "không nên"]):
                current_rec.append(line)
            elif line and not line.startswith("**"):
                current_desc.append(line)
    
    # Don't forget the last one
    if current_pair:
        if not current_severity:
            current_severity = parse_severity(" ".join(current_desc))
        interactions.append({
            "drug_pair": current_pair,
            "severity": current_severity,
            "description": " ".join(current_desc)[:500] if current_desc else "Có tương tác thuốc",
            "recommendation": " ".join(current_rec)[:300] if current_rec else "Cần tham khảo ý kiến bác sĩ"
        })
    
    return interactions


def extract_thinking_steps(text: str) -> List[str]:
    """Extract thinking steps từ text với format **Bước X:**"""
    steps = []
    pattern = r'\*\*Bước\s*\d+[^*]*\*\*:?\s*([^\*]+?)(?=\*\*Bước|\Z)'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    for i, match in enumerate(matches, 1):
        step_text = match.strip()
        if step_text:
            # Truncate long steps
            if len(step_text) > 200:
                step_text = step_text[:200] + "..."
            steps.append(f"Bước {i}: {step_text}")
    
    return steps if steps else ["Đã phân tích yêu cầu về thuốc"]


def extract_alternative_drugs(text: str) -> List[str]:
    """Extract thuốc thay thế từ text."""
    alternatives = []
    
    # Common alternative drug patterns
    patterns = [
        r'Thay thế[^:]*:\s*([^\n]+)',
        r'thay thế\s+bằng\s+(\w+(?:\s+\d+\w*)?)',
        r'Paracetamol\s*(?:\d+(?:-\d+)?mg)?',
        r'Celecoxib(?:\s+\([^)]+\))?',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, str) and len(match) > 2:
                match = match.strip()
                if match not in alternatives:
                    alternatives.append(match)
    
    return alternatives[:5]  # Max 5


def extract_contraindication(text: str) -> Optional[str]:
    """Extract cảnh báo chống chỉ định."""
    patterns = [
        r'KHÔNG[^.]+(?:dùng|sử dụng)[^.]+\.',
        r'chống chỉ định[^.]+\.',
        r'Cấm[^.]+\.',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    
    return None


def pharmacist_node(state: AgentState) -> Dict[str, Any]:
    """
    Pharmacist Agent (Dược sĩ lâm sàng) - Real Token Streaming
    
    Flow:
    1. Nếu cần tools -> return tool calls
    2. LLM text thinking
    3. Parse text thành structured response
    """
    logging_node_execution("PHARMACIST")
    messages = state["messages"]
    
    # DEBUG: Log messages being passed to pharmacist
    print(f"[PHARMACIST] Number of messages: {len(messages)}")
    for i, msg in enumerate(messages):
        msg_type = type(msg).__name__
        content = getattr(msg, 'content', '')[:100] if hasattr(msg, 'content') else 'N/A'
        print(f"[PHARMACIST] Message {i}: type={msg_type}, content_preview={content}")
    
    # Convert dict messages to LangChain message objects
    # LLM cần HumanMessage/AIMessage objects, không phải dict
    # CRITICAL: Filter out AI responses cũ để tránh confuse LLM
    converted_messages = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            # Keep user messages
            converted_messages.append(msg)
        elif isinstance(msg, AIMessage):
            # Skip AIMessage nếu content là JSON hoặc rỗng (response cũ từ agent)
            content = msg.content or ""
            if content.startswith("```") or content.startswith("{") or len(content) < 10:
                print(f"[PHARMACIST] Skipping old AIMessage: {content[:50]}...")
                continue
            # Keep AI messages with actual text content (conversation history)
            converted_messages.append(msg)
        elif isinstance(msg, SystemMessage):
            converted_messages.append(msg)
        elif isinstance(msg, dict):
            # Convert dict to appropriate message type
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if not content:
                continue  # Skip empty messages
            if role == 'user':
                converted_messages.append(HumanMessage(content=content))
            elif role == 'assistant':
                # Skip assistant messages that look like JSON
                if content.startswith("```") or content.startswith("{"):
                    print(f"[PHARMACIST] Skipping JSON assistant message: {content[:50]}...")
                    continue
                converted_messages.append(AIMessage(content=content))
            elif role == 'system':
                converted_messages.append(SystemMessage(content=content))
            else:
                converted_messages.append(HumanMessage(content=content))
        else:
            content = getattr(msg, 'content', str(msg))
            if content:
                converted_messages.append(HumanMessage(content=content))
    
    print(f"[PHARMACIST] Converted {len(converted_messages)} messages to LangChain format")
    
    # Ensure we have at least one user message
    if not any(isinstance(m, HumanMessage) for m in converted_messages):
        print("[PHARMACIST] WARNING: No user message found in converted messages!")
        # Try to find user message from original messages
        for msg in messages:
            if isinstance(msg, dict) and msg.get('role') == 'user':
                converted_messages.append(HumanMessage(content=msg.get('content', '')))
                break
    
    prompt = [SystemMessage(content=PHARMACIST_THINKING_PROMPT)] + converted_messages

    
    # Get last user message for context
    # Support cả HumanMessage objects và dict messages
    last_user_message = ""
    for msg in reversed(messages):
        # Case 1: LangChain HumanMessage object
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break
        # Case 2: Dict message với role='user'
        elif isinstance(msg, dict):
            if msg.get('role') == 'user' and msg.get('content'):
                last_user_message = msg['content']
                break
    
    print(f"[PHARMACIST] Last user message: {last_user_message[:100] if last_user_message else '(empty)'}")
    
    # Phase 1: Gọi LLM với tools binding (sync để tránh event loop issues)
    response = llm_pharmacist_with_tools.invoke(prompt)
    
    # Nếu LLM quyết định gọi tool
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"[PHARMACIST] Tool calls detected: {[tc['name'] for tc in response.tool_calls]}")
        return {
            "messages": [response],
            "current_agent": "pharmacist"
        }
    
    # Phase 2: Parse text response thành structured format
    text_analysis = response.content
    print(f"[PHARMACIST] Text analysis length: {len(text_analysis)} chars")
    print(f"[PHARMACIST] Raw response content: {text_analysis[:200] if text_analysis else '(empty)'}...")
    
    try:
        # Extract components từ text
        thinking_steps = extract_thinking_steps(text_analysis)
        drug_interactions = extract_drug_interactions_from_text(text_analysis)
        alternative_drugs = extract_alternative_drugs(text_analysis)
        contraindication = extract_contraindication(text_analysis)
        
        print(f"[PHARMACIST] Found {len(drug_interactions)} interactions")
        print(f"[PHARMACIST] Found {len(alternative_drugs)} alternatives")
        
        # Build structured response
        structured_data = {
            "thinking_progress": thinking_steps,
            "final_response": extract_final_response(text_analysis, "Khuyến nghị"),
            "confidence_score": 0.85 if drug_interactions else 0.7,
            "drug_interactions": drug_interactions if drug_interactions else None,
            "alternative_drugs": alternative_drugs if alternative_drugs else None,
            "dosage_guidance": None,  # Extract if needed
            "contraindication_warning": contraindication,
        }
        
        # Tạo message với structured data trong additional_kwargs
        message = AIMessage(
            content=text_analysis,  # Full text cho streaming display
            additional_kwargs={
                "agent": "pharmacist",
                "structured_response": structured_data,
                "thinking_progress": thinking_steps,
                "confidence_score": structured_data["confidence_score"]
            }
        )
        
    except Exception as e:
        print(f"[PHARMACIST] Parse error: {e}")
        # Fallback - still return the text
        message = AIMessage(
            content=text_analysis,
            additional_kwargs={
                "agent": "pharmacist",
                "structured_response": {
                    "final_response": text_analysis,
                    "confidence_score": 0.6,
                },
                "thinking_progress": ["Đã xử lý yêu cầu về thuốc"],
            }
        )
    
    return {
        "messages": [message],
        "current_agent": "pharmacist"
    }
