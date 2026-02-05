# apps/ai_engine/agents/utils.py
"""
Global constants and utilities for all AI agents.

Chứa các quy tắc chung áp dụng cho tất cả agents:
- Quy tắc ngôn ngữ (Vietnamese with medical English terms)
- Quy tắc JSON output bắt buộc
- Quy tắc thinking_progress để tránh hallucination
"""

from typing import Dict, Any
from langchain_core.messages import AIMessage


# =============================================================================
# GLOBAL LANGUAGE RULE
# =============================================================================

GLOBAL_LANGUAGE_RULE = """
## Quy Tắc Ngôn Ngữ

Bạn PHẢI trả lời bằng tiếng Việt. Tuy nhiên, đối với các thuật ngữ y khoa chuyên môn 
(bệnh, thuốc, triệu chứng, xét nghiệm), hãy giữ nguyên tiếng Anh hoặc cung cấp 
thuật ngữ tiếng Anh trong ngoặc đơn.

Ví dụ cách trả lời đúng:
- "Bệnh nhân bị Hypertension (Tăng huyết áp)"
- "Cần làm xét nghiệm Complete Blood Count (CBC)"
- "Tôi nghi ngờ đây là Acute Myocardial Infarction (Nhồi máu cơ tim cấp)"

KHÔNG được trả lời hoàn toàn bằng tiếng Anh.
KHÔNG sử dụng emoji trong phản hồi. Thay vào đó, dùng các mã code như [CODE_RED], [SEVERITY_MAJOR].
"""


# =============================================================================
# GLOBAL JSON OUTPUT RULE (BẮT BUỘC)
# =============================================================================

GLOBAL_JSON_OUTPUT_RULE = """
## Quy Tắc Đầu Ra JSON (BẮT BUỘC)

Bạn PHẢI trả về response theo JSON schema được cung cấp. KHÔNG được trả về text tự do.

### Field thinking_progress (BẮT BUỘC)

Field `thinking_progress` là ARRAY chứa từng bước suy nghĩ của bạn TRƯỚC KHI đưa ra kết luận.
Đây là field quan trọng nhất để:
1. Đảm bảo suy luận có căn cứ, tránh hallucination
2. Cho phép debug và trace quá trình quyết định
3. Tăng độ tin cậy của phản hồi

### Format thinking_progress:

```json
{
  "thinking_progress": [
    "Bước 1: Xác định vấn đề - [mô tả ngắn gọn vấn đề]",
    "Bước 2: Phân tích dữ liệu - [dữ liệu/thông tin đã có]",
    "Bước 3: Đánh giá các phương án - [các lựa chọn có thể]",
    "Bước 4: Kết luận - [quyết định cuối cùng và lý do]"
  ],
  "final_response": "Phản hồi chính gửi cho người dùng...",
  "confidence_score": 0.85
}
```

### Lưu Ý Quan Trọng:

1. LUÔN có ít nhất 2-4 bước suy nghĩ trong thinking_progress
2. Mỗi bước phải cụ thể, không chung chung
3. confidence_score phản ánh độ chắc chắn của bạn (0.0-1.0)
4. Nếu không chắc chắn, ghi rõ trong thinking_progress và đặt confidence_score thấp
5. KHÔNG bịa thông tin - nếu thiếu data, nói rõ trong thinking_progress
"""


# =============================================================================
# THINKING PROGRESS EXAMPLES BY AGENT TYPE
# =============================================================================

THINKING_EXAMPLES = {
    "clinical": """
Ví dụ thinking_progress cho Clinical Agent:
```json
{
  "thinking_progress": [
    "Bước 1: Xác định triệu chứng chính - Bệnh nhân báo đau ngực trái, khó thở khi gắng sức",
    "Bước 2: Đối chiếu tiền sử - Có tiền sử Hypertension 5 năm, đang dùng Amlodipine",
    "Bước 3: Đánh giá mức độ khẩn cấp - Triệu chứng gợi ý Angina Pectoris, cần loại trừ ACS",
    "Bước 4: Đề xuất xét nghiệm - ECG + Troponin để đánh giá, nếu bình thường có thể làm stress test"
  ],
  "final_response": "Dựa trên triệu chứng đau ngực trái...",
  "symptom_analysis": "Đau ngực điển hình, liên quan gắng sức",
  "differential_diagnosis": ["Stable Angina", "Unstable Angina", "GERD"],
  "recommended_tests": ["ECG", "Troponin I", "Chest X-ray"],
  "requires_urgent_care": false,
  "confidence_score": 0.75
}
```
""",
    "triage": """
Ví dụ thinking_progress cho Triage Agent:
```json
{
  "thinking_progress": [
    "Bước 1: Kiểm tra chỉ số sinh hiệu - BP 180/110, HR 120, SpO2 95%",
    "Bước 2: Đánh giá theo ngưỡng - BP > 180 là Hypertensive Crisis, HR tăng",
    "Bước 3: Xác định mức độ khẩn cấp - Có dấu hiệu tổn thương cơ quan đích?",
    "Bước 4: Phân loại - CODE_RED, cần xử lý dưới 10 phút"
  ],
  "triage_code": "CODE_RED",
  "final_response": "[CẢNH BÁO] Hypertensive Crisis...",
  "trigger_alert": true,
  "confidence_score": 0.95
}
```
""",
    "pharmacist": """
Ví dụ thinking_progress cho Pharmacist Agent:
```json
{
  "thinking_progress": [
    "Bước 1: Xác định thuốc cần kiểm tra - Warfarin + Aspirin",
    "Bước 2: Tra cứu tương tác - Warfarin + NSAIDs có Major Interaction",
    "Bước 3: Đánh giá nguy cơ - Tăng nguy cơ xuất huyết đáng kể",
    "Bước 4: Đề xuất thay thế - Dùng Paracetamol thay Aspirin nếu mục đích giảm đau"
  ],
  "final_response": "[SEVERITY_MAJOR] Phát hiện tương tác nghiêm trọng...",
  "drug_interactions": [...],
  "alternative_drugs": ["Paracetamol"],
  "confidence_score": 0.9
}
```
"""
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def format_structured_response_to_message(response: Any, agent_name: str) -> AIMessage:
    """
    Chuyển đổi Pydantic structured response thành AIMessage cho LangGraph.
    
    Args:
        response: Pydantic model response từ structured output
        agent_name: Tên agent tạo response
    
    Returns:
        AIMessage chứa final_response và metadata
    """
    # Extract final_response for user-facing content
    content = response.final_response if hasattr(response, 'final_response') else str(response)
    
    # Include full structured data in additional_kwargs
    response_dict = response.model_dump() if hasattr(response, 'model_dump') else {}
    
    return AIMessage(
        content=content,
        additional_kwargs={
            "agent": agent_name,
            "structured_response": response_dict,
            "thinking_progress": response_dict.get("thinking_progress", []),
            "confidence_score": response_dict.get("confidence_score", 0.0)
        }
    )


def extract_thinking_progress(message: AIMessage) -> list:
    """
    Trích xuất thinking_progress từ AIMessage.
    
    Args:
        message: AIMessage từ agent
    
    Returns:
        List các bước suy nghĩ
    """
    return message.additional_kwargs.get("thinking_progress", [])


def extract_confidence_score(message: AIMessage) -> float:
    """
    Trích xuất confidence_score từ AIMessage.
    
    Args:
        message: AIMessage từ agent
    
    Returns:
        Confidence score (0.0 - 1.0)
    """
    return message.additional_kwargs.get("confidence_score", 0.0)

