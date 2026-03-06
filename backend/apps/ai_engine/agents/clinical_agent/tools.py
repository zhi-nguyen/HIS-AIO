# apps/ai_engine/agents/clinical_agent/tools.py
"""
Tools cho Clinical Agent (Bác sĩ chẩn đoán)

Cung cấp các tool lưu nháp hồ sơ khám bệnh và tra cứu mã ICD-10.
"""

from langchain_core.tools import tool
import json

# Import Services & Models
from apps.medical_services.emr.services import ClinicalService
from apps.core_services.core.models import ICD10Code


@tool
def save_clinical_draft(visit_id: str, diagnosis_data: str) -> str:
    """
    Lưu nháp thông tin khám bệnh (triệu chứng, bệnh sử, chẩn đoán sơ bộ) vào hồ sơ.
    Sử dụng tool này khi cần cập nhật hồ sơ bệnh án từ thông tin đang trao đổi.
    
    Args:
        visit_id: ID của lượt khám (Visit ID).
        diagnosis_data: Chuỗi JSON chứa các trường cần lưu:
            - chief_complaint: Lý do khám.
            - history_of_present_illness: Bệnh sử.
            - physical_exam: Khám lâm sàng.
            - final_diagnosis: Chẩn đoán (nếu có).
            - treatment_plan: Hướng điều trị.
    
    Returns:
        Thông báo xác nhận lưu thành công.
    """
    try:
        data = json.loads(diagnosis_data)
        record = ClinicalService.save_draft_diagnosis(visit_id, data)
        return f"Đã lưu nháp hồ sơ thành công cho Visit {record.visit.visit_code}."
    except json.JSONDecodeError:
        return "Lỗi: diagnosis_data phải là chuỗi JSON hợp lệ."
    except Exception as e:
        return f"Lỗi khi lưu hồ sơ: {str(e)}"


@tool
def lookup_icd10(keyword: str) -> str:
    """
    Tìm kiếm mã bệnh ICD-10 theo từ khóa.
    
    Args:
        keyword: Từ khóa tên bệnh hoặc mã bệnh (ví dụ: "Sốt xuất huyết", "J00").
    
    Returns:
        Danh sách các mã ICD-10 phù hợp (tối đa 5 kết quả).
    """
    results = ICD10Code.objects.filter(name__icontains=keyword) | ICD10Code.objects.filter(code__icontains=keyword)
    results = results[:5]
    
    if not results:
        return f"Không tìm thấy mã ICD-10 nào cho từ khóa '{keyword}'."
    
    output = "Kết quả tìm kiếm ICD-10:\n"
    for item in results:
        output += f"- {item.code}: {item.name}\n"
    return output


@tool
def search_clinical_guideline(diagnosis_keyword: str) -> str:
    """
    Tìm kiếm phác đồ điều trị chuẩn (clinical guideline) theo từ khóa chẩn đoán.
    Dùng semantic search qua RAG vector database (collection 'guidelines').
    Trả về tối đa 3 phác đồ liên quan nhất.

    Args:
        diagnosis_keyword: Từ khóa chẩn đoán hoặc tên bệnh (VD: 'tăng huyết áp', 'viêm phổi').

    Returns:
        Danh sách phác đồ điều trị liên quan, hoặc thông báo không tìm thấy.
    """
    import asyncio
    from apps.ai_engine.rag_service.vector_service import VectorService
    from apps.ai_engine.rag_service.embeddings import EmbeddingService

    async def _search():
        vector_service = VectorService()
        embedding_service = EmbeddingService()

        # Embed từ khóa chẩn đoán
        embedding = await embedding_service.embed_text(diagnosis_keyword)

        # Semantic search trong collection 'guidelines'
        results = await vector_service.search(
            collection_name='guidelines',
            query_embedding=embedding,
            n_results=3,
        )
        return results

    try:
        results = asyncio.run(_search())
    except RuntimeError:
        # Đã có event loop (trong async context) — dùng nest_asyncio hoặc direct call
        import nest_asyncio
        nest_asyncio.apply()
        results = asyncio.run(_search())
    except Exception as e:
        return f"Lỗi khi tìm kiếm phác đồ: {str(e)}"

    if not results or not results.get('documents'):
        return f"Không tìm thấy phác đồ điều trị chuẩn cho '{diagnosis_keyword}'. Vui lòng tham khảo tài liệu chuyên ngành trực tiếp."

    docs = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]

    output_lines = [f"📋 Phác đồ điều trị cho '{diagnosis_keyword}':\n"]
    for i, (doc, meta) in enumerate(zip(docs, metadatas), 1):
        title = meta.get('title', f'Phác đồ {i}')
        source = meta.get('source', 'Không rõ nguồn')
        version = meta.get('version', '')
        # Chỉ lấy 500 ký tự đầu của nội dung
        snippet = doc[:500] + "..." if len(doc) > 500 else doc
        output_lines.append(f"**{i}. {title}** (Nguồn: {source} {version})")
        output_lines.append(snippet)
        output_lines.append("")

    return "\n".join(output_lines)

