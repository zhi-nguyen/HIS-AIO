# apps/ai_engine/agents/pharmacist_agent/node.py
"""
Pharmacist Agent Node - Dược sĩ lâm sàng

Sử dụng 2-phase approach cho agents có tools:
1. Phase 1: LLM với tools để thực hiện drug interaction check
2. Phase 2: Structured output để format response
"""

from typing import Dict, Any
from langchain_core.messages import SystemMessage, AIMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_pharmacist_with_tools, llm_flash, logging_node_execution
from apps.ai_engine.agents.schemas import PharmacistResponse
from apps.ai_engine.agents.utils import format_structured_response_to_message
from .prompts import PHARMACIST_PROMPT


def pharmacist_node(state: AgentState) -> Dict[str, Any]:
    """
    Pharmacist Agent (Dược sĩ lâm sàng) - Has Drug Tools
    
    Sử dụng 2-phase approach:
    - Nếu cần gọi tools -> trả về AIMessage với tool_calls
    - Nếu không cần tools -> trả về structured JSON response
    """
    logging_node_execution("PHARMACIST")
    messages = state["messages"]
    prompt = [SystemMessage(content=PHARMACIST_PROMPT)] + messages
    
    # Phase 1: Gọi LLM với tools binding
    response = llm_pharmacist_with_tools.invoke(prompt)
    
    # Nếu LLM quyết định gọi tool, trả về để LangGraph xử lý
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"[PHARMACIST] Tool calls detected: {[tc['name'] for tc in response.tool_calls]}")
        return {
            "messages": [response],
            "current_agent": "pharmacist"
        }
    
    # Phase 2: Parse response thành structured format
    try:
        llm_structured = llm_flash.with_structured_output(PharmacistResponse)
        
        format_prompt = [
            SystemMessage(content=f"""Bạn là Pharmacist Agent. Hãy format lại phản hồi sau thành JSON theo schema yêu cầu.
            
Phản hồi gốc: {response.content}

JSON Schema yêu cầu:
{{
  "thinking_progress": ["Bước 1...", "Bước 2..."],
  "final_response": "Phản hồi đầy đủ...",
  "confidence_score": 0.0-1.0,
  "drug_interactions": [
    {{"drug_pair": "...", "severity": "SEVERITY_MAJOR|MODERATE|MINOR", "description": "...", "recommendation": "..."}}
  ],
  "alternative_drugs": ["Thuốc thay thế"],
  "dosage_guidance": "Hướng dẫn liều",
  "contraindication_warning": "Cảnh báo nếu có"
}}""")
        ] + messages
        
        structured_response = llm_structured.invoke(format_prompt)
        
        # Log thinking progress
        print(f"[PHARMACIST] Thinking Progress:")
        for step in structured_response.thinking_progress:
            print(f"  - {step}")
        print(f"[PHARMACIST] Confidence: {structured_response.confidence_score}")
        if structured_response.drug_interactions:
            print(f"[PHARMACIST] Interactions found: {len(structured_response.drug_interactions)}")
        
        message = format_structured_response_to_message(structured_response, "pharmacist")
        
    except Exception as e:
        print(f"[PHARMACIST] Structured output error: {e}")
        message = AIMessage(
            content=response.content,
            additional_kwargs={
                "agent": "pharmacist",
                "thinking_progress": [],
                "structured_response": None
            }
        )
    
    return {
        "messages": [message],
        "current_agent": "pharmacist"
    }
