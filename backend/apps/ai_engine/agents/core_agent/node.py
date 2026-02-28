# apps/ai_engine/agents/core_agent/node.py
"""
Supervisor Node - Routes requests to specialist agents

REFACTORED cho Real Token Streaming:
- LLM output text thinking (stream được)  
- Parse text để extract agent decision
"""

from typing import Dict, Any, Literal, Optional
import re
from langchain_core.messages import SystemMessage, AIMessage
from pydantic import BaseModel, Field

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_pro, logging_node_execution
from .prompts import SUPERVISOR_SYSTEM_PROMPT
from apps.ai_engine.agents.security import (
    InputSanitizer, 
    is_agent_allowed, 
    REJECTION_MESSAGE,
)


# ==============================================================================
# AGENT NAME MAPPINGS
# ==============================================================================

VALID_AGENTS = {
    "consultant", "triage", "clinical", "pharmacist", 
    "paraclinical", "summarize", "marketing", "human", "end"
}

AGENT_ALIASES = {
    # Vietnamese aliases
    "bác sĩ": "clinical",
    "bac si": "clinical", 
    "dược sĩ": "pharmacist",
    "duoc si": "pharmacist",
    "tư vấn": "consultant",
    "tu van": "consultant",
    "lễ tân": "consultant",
    "le tan": "consultant",
    "xét nghiệm": "paraclinical",
    "xet nghiem": "paraclinical",
    "lab": "paraclinical",
    "cấp cứu": "triage",
    "cap cuu": "triage",
    "khẩn cấp": "triage",
    "khan cap": "triage",
}


def extract_agent_from_text(text: str) -> str:
    """
    Extract agent name từ text response.
    
    Tìm patterns như:
    - "Chọn agent: PHARMACIST"
    - "next_agent: CLINICAL"
    - "Routing to: TRIAGE"
    """
    text_lower = text.lower()
    
    # Pattern 1: "Chọn agent: XXX"
    patterns = [
        r'chọn\s+agent\s*:\s*(\w+)',
        r'next_agent\s*:\s*["\']?(\w+)["\']?',
        r'routing\s+to\s*:\s*(\w+)',
        r'chuyển\s+(?:đến|tới)\s*:\s*(\w+)',
        r'\*\*bước\s*4[^*]*\*\*[:\s]*.*?chọn[^:]*:\s*(\w+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
        if match:
            agent = match.group(1).lower().strip()
            if agent in VALID_AGENTS:
                return agent
            # Check aliases
            if agent in AGENT_ALIASES:
                return AGENT_ALIASES[agent]
    
    # Pattern 2: Tìm agent name xuất hiện trong "Bước 4" section
    step4_pattern = r'\*\*bước\s*4[^*]*\*\*[:\s]*(.*)'
    step4_match = re.search(step4_pattern, text_lower, re.IGNORECASE | re.DOTALL)
    if step4_match:
        step4_text = step4_match.group(1)[:200]  # First 200 chars
        for agent in VALID_AGENTS:
            if agent in step4_text:
                return agent
    
    # Pattern 3: Tìm agent name xuất hiện nhiều nhất
    agent_counts = {}
    for agent in VALID_AGENTS:
        count = text_lower.count(agent)
        if count > 0:
            agent_counts[agent] = count
    
    if agent_counts:
        # Get agent with highest count, but prioritize certain patterns
        # Exclude common words that might match
        for agent in ["pharmacist", "clinical", "triage", "paraclinical"]:
            if agent in agent_counts and agent_counts[agent] >= 2:
                return agent
        
        return max(agent_counts, key=agent_counts.get)
    
    # Default fallback
    return "consultant"


def extract_routing_reason(text: str) -> str:
    """Extract routing reason từ text."""
    patterns = [
        r'lý\s+do\s*:\s*([^\n]+)',
        r'routing_reason\s*:\s*["\']([^"\']+)["\']',
        r'reason\s*:\s*([^\n]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Fallback: get last line of step 4
    step4_pattern = r'\*\*bước\s*4[^*]*\*\*[:\s]*([^*]+)'
    match = re.search(step4_pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        lines = match.group(1).strip().split('\n')
        for line in reversed(lines):
            if line.strip() and len(line.strip()) > 10:
                return line.strip()[:200]
    
    return "Đã phân tích và chọn agent phù hợp"


def extract_thinking_steps(text: str) -> list:
    """Extract thinking steps từ text."""
    steps = []
    pattern = r'\*\*Bước\s*(\d+)[^*]*\*\*[:\s]*([^*]+?)(?=\*\*Bước|\Z)'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    for step_num, content in matches:
        content = content.strip()
        if content:
            # Truncate long content
            if len(content) > 150:
                content = content[:150] + "..."
            steps.append(f"Bước {step_num}: {content}")
    
    return steps if steps else ["Đã phân tích yêu cầu người dùng"]


def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    Supervisor node - phân tích và route đến agent phù hợp.
    
    Flow:
    1. LLM output text thinking (được stream)
    2. Parse text để extract agent decision
    
    Returns:
        Dict với next_agent và thông tin routing
    """
    logging_node_execution("SUPERVISOR")
    messages = state["messages"]
    
    # =========================================================================
    # LAYER 1: INPUT SANITIZATION & INJECTION DETECTION
    # =========================================================================
    last_user_msg = ""
    for msg in reversed(messages):
        if hasattr(msg, 'content'):
            last_user_msg = msg.content
            break
        elif isinstance(msg, dict) and msg.get('role') == 'user':
            last_user_msg = msg.get('content', '')
            break
    
    sanitized_input, is_safe = InputSanitizer.check_and_sanitize(last_user_msg)
    
    if not is_safe:
        print(f"[SUPERVISOR] SECURITY: Prompt injection detected! Blocking.")
        message = AIMessage(
            content=REJECTION_MESSAGE,
            additional_kwargs={
                "agent": "supervisor",
                "security_block": True,
                "thinking_progress": ["Phát hiện yêu cầu bất thường - từ chối xử lý."],
            }
        )
        return {
            "messages": [message],
            "next_agent": "end",
            "current_agent": "supervisor"
        }
    
    # Call LLM với text thinking prompt
    prompt_messages = [SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT)] + messages
    
    try:
        # LLM sẽ stream text thinking - streaming service sẽ capture
        response = llm_pro.invoke(prompt_messages)
        text_response = response.content
        
        # Parse text để extract routing decision
        next_agent = extract_agent_from_text(text_response)
        routing_reason = extract_routing_reason(text_response)
        thinking_steps = extract_thinking_steps(text_response)
        
        # Log cho debug
        print(f"[SUPERVISOR] Thinking Steps:")
        for step in thinking_steps[:4]:
            print(f"  - {step[:80]}...")
        print(f"[SUPERVISOR] Routing to: {next_agent}")
        print(f"[SUPERVISOR] Reason: {routing_reason[:100]}...")
        
        # Create AIMessage với structured data trong additional_kwargs
        message = AIMessage(
            content=text_response,
            additional_kwargs={
                "agent": "supervisor",
                "structured_response": {
                    "thinking_progress": thinking_steps,
                    "next_agent": next_agent.upper(),
                    "routing_reason": routing_reason,
                },
                "thinking_progress": thinking_steps,
            }
        )
        
    except Exception as e:
        print(f"[SUPERVISOR] Error: {e}")
        print(f"[SUPERVISOR] Fallback to CONSULTANT")
        next_agent = "consultant"
        message = AIMessage(
            content=f"Đang chuyển đến bộ phận tư vấn...",
            additional_kwargs={
                "agent": "supervisor",
                "thinking_progress": ["Fallback routing"],
            }
        )

    # =========================================================================
    # LAYER 2: AGENT ACCESS CONTROL (check user role vs target agent)
    # =========================================================================
    user_context = state.get("user_context") or {}
    staff_role = user_context.get("staff_role", "ANONYMOUS")
    
    if not is_agent_allowed(staff_role, next_agent):
        print(f"[SUPERVISOR] RBAC: Role '{staff_role}' denied access to agent '{next_agent}'. Redirecting to consultant.")
        next_agent = "consultant"
    
    return {
        "messages": [message],
        "next_agent": next_agent,
        "current_agent": "supervisor"
    }
