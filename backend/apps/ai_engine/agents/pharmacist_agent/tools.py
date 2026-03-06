# apps/ai_engine/agents/pharmacist_agent/tools.py
"""
Tools cho Pharmacist Agent (Dược sĩ lâm sàng)

Cung cấp các tool kiểm tra tương tác thuốc và gợi ý thuốc thay thế.
CDSS Track 3: check_drug_interaction và check_patient_allergy giờ dùng
CDSSService thay vì hardcoded dict — dữ liệu quản lý trong DrugInteraction model.
"""

from langchain_core.tools import tool
from typing import List


# ==============================================================================
# TOOLS
# ==============================================================================

@tool
def check_drug_interaction(drug_names: List[str]) -> str:
    """
    Kiểm tra tương tác giữa danh sách các thuốc.
    Trả về cảnh báo nếu có tương tác nguy hiểm.
    Dữ liệu từ DrugInteraction model (quản trị viên cập nhật qua Admin).

    Args:
        drug_names: Danh sách tên thuốc hoặc hoạt chất (ví dụ: ["Aspirin", "Warfarin"]).

    Returns:
        Kết quả kiểm tra tương tác với mức độ nghiêm trọng.
    """
    from apps.medical_services.pharmacy.services.cdss_service import CDSSService

    alerts = CDSSService.check_drug_interaction(drug_names)

    if not alerts:
        drug_str = ", ".join(drug_names)
        return f"[AN TOÀN] Không tìm thấy tương tác đáng kể giữa: {drug_str}."

    lines = []
    for alert in alerts:
        lines.append(alert['message'])
        lines.append(f"  Khuyến nghị: {alert.get('recommendation', '')}")
    return "\n".join(lines)


@tool
def suggest_drug_alternative(drug_name: str, reason: str) -> str:
    """
    Gợi ý thuốc thay thế khi thuốc hiện tại bị chống chỉ định hoặc hết hàng.
    
    Args:
        drug_name: Tên thuốc cần thay thế.
        reason: Lý do cần thay thế (ví dụ: "dị ứng", "hết hàng", "chống chỉ định").
    
    Returns:
        Danh sách thuốc thay thế được gợi ý.
    """
    # TODO: Kết nối với cơ sở dữ liệu thuốc
    
    drug_lower = drug_name.lower()
    
    alternatives = {
        "aspirin": (
            f"[GỢI Ý THAY THẾ CHO ASPIRIN] (Lý do: {reason})\n"
            f"1. Paracetamol 500mg - Nếu mục đích giảm đau, hạ sốt\n"
            f"2. Clopidogrel 75mg - Nếu cần kháng kết tập tiểu cầu\n"
            f"3. Aspirin Enteric-coated - Nếu vấn đề là kích ứng dạ dày"
        ),
        "ibuprofen": (
            f"[GỢI Ý THAY THẾ CHO IBUPROFEN] (Lý do: {reason})\n"
            f"1. Paracetamol 500mg - An toàn cho đa số bệnh nhân\n"
            f"2. Celecoxib 100mg - COX-2 selective, ít kích ứng dạ dày\n"
            f"3. Naproxen 250mg - Nếu cần tác dụng kháng viêm kéo dài"
        ),
        "metformin": (
            f"[GỢI Ý THAY THẾ CHO METFORMIN] (Lý do: {reason})\n"
            f"1. Sitagliptin 100mg - DPP-4 inhibitor, ít gây tiêu chảy\n"
            f"2. Empagliflozin 10mg - SGLT2 inhibitor, bảo vệ tim mạch\n"
            f"3. Glimepiride 2mg - Sulfonylurea, nếu cần hạ đường nhanh"
        ),
    }
    
    if drug_lower in alternatives:
        return alternatives[drug_lower]
    
    return f"Đang tra cứu thuốc thay thế cho {drug_name}. Vui lòng chờ hoặc tham vấn dược sĩ trực tiếp."


@tool
def check_patient_allergy(patient_id: str, drug_names: List[str]) -> str:
    """
    Kiểm tra bệnh nhân có dị ứng với thuốc đang kê không.
    Tra cứu từ hồ sơ dị ứng (PatientAllergy) và so sánh với hoạt chất thuốc.

    Args:
        patient_id: UUID của bệnh nhân.
        drug_names: Danh sách tên thuốc hoặc hoạt chất đang kê đơn.

    Returns:
        Thông báo cảnh báo dị ứng hoặc xác nhận an toàn.
    """
    from apps.medical_services.pharmacy.services.cdss_service import CDSSService

    alerts = CDSSService.check_allergy_alert(patient_id, drug_names)

    if not alerts:
        return f"[AN TOÀN] Không phát hiện dị ứng với các thuốc: {', '.join(drug_names)}."

    lines = []
    for alert in alerts:
        lines.append(alert['message'])
    return "\n".join(lines)

