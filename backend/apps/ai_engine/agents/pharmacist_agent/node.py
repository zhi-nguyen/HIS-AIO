# apps/ai_engine/agents/pharmacist_agent/node.py
"""
Pharmacist Agent Node - Dược sĩ lâm sàng

Sử dụng 2-phase approach cho agents có tools:
1. Phase 1: LLM với tools để thực hiện drug interaction check
2. Phase 2: Structured output để format response
"""

from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_pharmacist_with_tools, llm_flash, logging_node_execution
from apps.ai_engine.agents.schemas import PharmacistResponse, DrugInteraction
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
    
    # Get last user message for context
    last_user_message = ""
    for msg in reversed(messages):
        if hasattr(msg, 'content') and isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break
    
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
        
        # Tạo prompt rõ ràng hơn với cả context và response
        format_prompt = [
            SystemMessage(content=f"""Bạn là Dược sĩ lâm sàng (Pharmacist Agent). 

NHIỆM VỤ: Phân tích yêu cầu của người dùng và phản hồi trước đó, sau đó tạo response JSON đầy đủ.

## Yêu cầu từ người dùng:
{last_user_message}

## Phản hồi ban đầu từ AI:
{response.content}

## YÊU CẦU OUTPUT:
Bạn PHẢI tạo JSON với các trường sau:

1. "thinking_progress": Mảng 4 bước suy nghĩ chi tiết
2. "final_response": Phản hồi đầy đủ, chi tiết về tương tác thuốc (KHÔNG phải "Đang kiểm tra...")
3. "confidence_score": 0.0-1.0
4. "drug_interactions": Mảng các tương tác thuốc với format:
   - drug_pair: "Thuốc A + Thuốc B"
   - severity: "SEVERITY_MAJOR" hoặc "SEVERITY_MODERATE" hoặc "SEVERITY_MINOR"
   - description: Mô tả chi tiết tương tác
   - recommendation: Khuyến nghị xử lý
5. "alternative_drugs": Mảng thuốc thay thế (nếu có)
6. "dosage_guidance": Hướng dẫn liều dùng
7. "contraindication_warning": Cảnh báo chống chỉ định

LƯU Ý QUAN TRỌNG:
- final_response phải là câu trả lời HOÀN CHỈNH, không phải placeholder
- Nếu có tương tác thuốc, phải liệt kê đầy đủ trong drug_interactions
- Dựa vào kiến thức y khoa để đưa ra thông tin chính xác
"""),
            HumanMessage(content=f"Hãy tạo JSON response đầy đủ cho yêu cầu: {last_user_message}")
        ]
        
        structured_response = llm_structured.invoke(format_prompt)
        
        # Log thinking progress
        print(f"[PHARMACIST] Thinking Progress:")
        for step in structured_response.thinking_progress:
            print(f"  - {step}")
        print(f"[PHARMACIST] Confidence: {structured_response.confidence_score}")
        if structured_response.drug_interactions:
            print(f"[PHARMACIST] Interactions found: {len(structured_response.drug_interactions)}")
            for interaction in structured_response.drug_interactions:
                print(f"    - {interaction.drug_pair}: {interaction.severity}")
        
        message = format_structured_response_to_message(structured_response, "pharmacist")
        
    except Exception as e:
        print(f"[PHARMACIST] Structured output error: {e}")
        # Fallback: Tạo response thủ công từ LLM response
        message = AIMessage(
            content=response.content,
            additional_kwargs={
                "agent": "pharmacist",
                "thinking_progress": ["Đã xử lý yêu cầu về tương tác thuốc"],
                "structured_response": {
                    "final_response": response.content,
                    "confidence_score": 0.7,
                    "drug_interactions": None,
                    "alternative_drugs": None,
                    "dosage_guidance": None,
                    "contraindication_warning": None
                }
            }
        )
    
    return {
        "messages": [message],
        "current_agent": "pharmacist"
    }
