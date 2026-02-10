# apps/ai_engine/agents/pharmacist_agent/tools.py
"""
Tools cho Pharmacist Agent (Dược sĩ lâm sàng)

Cung cấp các tool kiểm tra tương tác thuốc và gợi ý thuốc thay thế.
"""

from langchain_core.tools import tool
from typing import List


# ==============================================================================
# CONSTANTS
# ==============================================================================

class InteractionSeverity:
    """Mức độ tương tác thuốc."""
    MAJOR = "SEVERITY_MAJOR"       # Nghiêm trọng - KHÔNG dùng chung
    MODERATE = "SEVERITY_MODERATE" # Trung bình - Cần theo dõi
    MINOR = "SEVERITY_MINOR"       # Nhẹ - Có thể dùng, lưu ý

    @classmethod
    def get_description(cls, severity: str) -> str:
        """Lấy mô tả tiếng Việt cho mức độ."""
        descriptions = {
            cls.MAJOR: "Nghiêm trọng - KHÔNG được dùng chung, cần đổi thuốc",
            cls.MODERATE: "Trung bình - Cân nhắc kỹ, cần theo dõi chặt chẽ",
            cls.MINOR: "Nhẹ - Có thể dùng, lưu ý theo dõi"
        }
        return descriptions.get(severity, "Không xác định")


# ==============================================================================
# TOOLS
# ==============================================================================

@tool
def check_drug_interaction(drug_names: List[str]) -> str:
    """
    Kiểm tra tương tác giữa danh sách các thuốc.
    Trả về cảnh báo nếu có tương tác nguy hiểm.
    
    Args:
        drug_names: Danh sách tên thuốc (ví dụ: ["Aspirin", "Warfarin"]).
    
    Returns:
        Kết quả kiểm tra tương tác với mức độ nghiêm trọng.
    """
    # TODO: Kết nối với Drug Interaction Database (DrugBank API, RxNorm)
    
    drug_str = ", ".join(drug_names)
    drug_set = set(d.lower() for d in drug_names)
    
    # Các tương tác đã biết
    if {"aspirin", "warfarin"} <= drug_set:
        return (
            f"[{InteractionSeverity.MAJOR}] CẢNH BÁO TƯƠNG TÁC NGHIÊM TRỌNG\n"
            f"Aspirin + Warfarin: Tăng nguy cơ chảy máu nghiêm trọng.\n"
            f"Khuyến nghị: KHÔNG dùng chung. Thay Aspirin bằng Paracetamol nếu cần giảm đau."
        )
    
    if {"ibuprofen", "warfarin"} <= drug_set:
        return (
            f"[{InteractionSeverity.MAJOR}] CẢNH BÁO TƯƠNG TÁC NGHIÊM TRỌNG\n"
            f"Ibuprofen (NSAID) + Warfarin: Tăng nguy cơ xuất huyết tiêu hóa.\n"
            f"Khuyến nghị: Dùng Paracetamol thay thế. Theo dõi INR chặt chẽ."
        )
    
    if {"metformin", "alcohol"} <= drug_set:
        return (
            f"[{InteractionSeverity.MODERATE}] CẢNH BÁO\n"
            f"Metformin + Alcohol: Tăng nguy cơ nhiễm toan lactic.\n"
            f"Khuyến nghị: Hạn chế rượu bia khi đang dùng Metformin."
        )
    
    if {"lisinopril", "potassium"} <= drug_set or {"enalapril", "potassium"} <= drug_set:
        return (
            f"[{InteractionSeverity.MODERATE}] CẢNH BÁO\n"
            f"ACE Inhibitor + Potassium: Nguy cơ tăng kali máu.\n"
            f"Khuyến nghị: Theo dõi nồng độ kali máu định kỳ."
        )
    
    return f"[{InteractionSeverity.MINOR}] Không tìm thấy tương tác đáng kể giữa: {drug_str}."


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
