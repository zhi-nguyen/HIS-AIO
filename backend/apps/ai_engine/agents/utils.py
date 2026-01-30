# apps/ai_engine/agents/utils.py

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
