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
