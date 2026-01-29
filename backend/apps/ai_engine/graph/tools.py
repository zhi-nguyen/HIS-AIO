# apps/ai_engine/graph/tools.py
"""
LangChain Tools for Medical AI Agents

Cung cấp các công cụ (tools) cho agents sử dụng:
- Consultant: Đặt lịch hẹn, kiểm tra lịch trống
- Pharmacist: Kiểm tra tương tác thuốc, gợi ý thay thế
- Triage: Gửi cảnh báo khẩn cấp
"""

from langchain_core.tools import tool
from typing import List, Optional
from datetime import datetime


# ==============================================================================
# CODE CONSTANTS (Tường minh, có thể truy cập trong code)
# ==============================================================================

class TriageCode:
    """Mã phân loại cấp cứu theo tiêu chuẩn quốc tế."""
    BLUE = "CODE_BLUE"      # Hồi sức cấp cứu (ngừng tim, ngừng thở)
    RED = "CODE_RED"        # Cấp cứu khẩn (< 10 phút)
    YELLOW = "CODE_YELLOW"  # Khẩn cấp (< 60 phút)
    GREEN = "CODE_GREEN"    # Không khẩn cấp (có thể chờ)

    @classmethod
    def get_description(cls, code: str) -> str:
        """Lấy mô tả tiếng Việt cho mã code."""
        descriptions = {
            cls.BLUE: "Hồi sức cấp cứu - Ngừng tim/ngừng thở - Xử lý NGAY",
            cls.RED: "Cấp cứu khẩn - Đe dọa tính mạng - Xử lý trong 10 phút",
            cls.YELLOW: "Khẩn cấp - Cần chú ý - Xử lý trong 60 phút",
            cls.GREEN: "Không khẩn cấp - Ổn định - Có thể chờ theo thứ tự"
        }
        return descriptions.get(code, "Không xác định")


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
# TOOLS FOR CONSULTANT (NHÂN VIÊN TƯ VẤN / ĐẶT LỊCH)
# ==============================================================================

@tool
def check_appointment_slots(department: str, date: str) -> str:
    """
    Kiểm tra các khung giờ còn trống của một khoa trong ngày cụ thể.
    Sử dụng khi người dùng muốn biết lịch trống hoặc muốn đặt lịch hẹn.
    
    Args:
        department: Tên khoa (ví dụ: "Cardiology", "Tim mạch", "Pediatrics", "Nhi khoa").
        date: Ngày cần kiểm tra theo định dạng "YYYY-MM-DD" hoặc "hôm nay", "ngày mai".
    
    Returns:
        Thông tin các khung giờ còn trống.
    """
    # TODO: Kết nối với Database thực tế (ConsultationSession model)
    # from apps.medical_services.emr.models import Visit
    # available = Visit.objects.filter(department=department, date=date, status='available')
    
    # Mock logic cho demo
    dept_lower = department.lower()
    
    if "cardiology" in dept_lower or "tim" in dept_lower:
        return f"Khoa Tim mạch (Cardiology) ngày {date} còn trống các khung giờ: 08:00, 09:30, 14:00, 15:30."
    elif "pediatric" in dept_lower or "nhi" in dept_lower:
        return f"Khoa Nhi (Pediatrics) ngày {date} còn trống: 08:30, 10:00, 14:30, 16:00."
    elif "internal" in dept_lower or "nội" in dept_lower:
        return f"Khoa Nội Tổng Quát (Internal Medicine) ngày {date} còn trống: 07:30, 09:00, 14:00."
    else:
        return f"Khoa {department} ngày {date} còn trống lúc: 08:00, 10:30, 15:00."


@tool
def book_appointment(patient_name: str, department: str, date: str, time: str, phone: str) -> str:
    """
    Đặt lịch hẹn khám cho bệnh nhân.
    CHỈ sử dụng tool này SAU KHI người dùng đã xác nhận thời gian và cung cấp đầy đủ thông tin.
    
    Args:
        patient_name: Họ tên đầy đủ của bệnh nhân.
        department: Khoa cần đặt lịch.
        date: Ngày hẹn (YYYY-MM-DD).
        time: Khung giờ đã chọn (ví dụ: "08:00").
        phone: Số điện thoại liên hệ.
    
    Returns:
        Xác nhận đặt lịch với mã booking.
    """
    # TODO: Tạo bản ghi Visit/Appointment trong DB
    # from apps.medical_services.emr.models import Visit
    # visit = Visit.objects.create(...)
    
    booking_ref = f"BK-{phone[-4:]}-{datetime.now().strftime('%H%M')}"
    
    return (
        f"[ĐẶT LỊCH THÀNH CÔNG]\n"
        f"Mã đặt lịch: #{booking_ref}\n"
        f"Bệnh nhân: {patient_name}\n"
        f"Khoa: {department}\n"
        f"Thời gian: {date} lúc {time}\n"
        f"Điện thoại: {phone}\n"
        f"Lưu ý: Vui lòng đến trước 15 phút để làm thủ tục."
    )


# ==============================================================================
# TOOLS FOR PHARMACIST (DƯỢC SĨ LÂM SÀNG)
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


# ==============================================================================
# TOOLS FOR TRIAGE (ĐIỀU DƯỠNG PHÂN LUỒNG)
# ==============================================================================

@tool
def trigger_emergency_alert(level: str, location: str, patient_info: str, vitals: str = "") -> str:
    """
    Gửi cảnh báo khẩn cấp đến dashboard bệnh viện và đội ngũ y tế.
    CHỈ sử dụng khi phát hiện tình huống CODE_RED hoặc CODE_BLUE.
    
    Args:
        level: Mức độ cảnh báo - "RED", "BLUE", "YELLOW" hoặc dùng TriageCode constants.
        location: Vị trí bệnh nhân (ví dụ: "Sảnh tiếp nhận", "Phòng khám 201", "Online Chat").
        patient_info: Thông tin ngắn gọn về bệnh nhân (tên, tuổi nếu có).
        vitals: Các chỉ số sinh hiệu bất thường (nếu có).
    
    Returns:
        Xác nhận cảnh báo đã được gửi.
    """
    # TODO: Kết nối với WebSocket/Notification Service
    # from apps.core_services.notifications.services import send_emergency_alert
    # send_emergency_alert(level=level, location=location, ...)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    alert_id = f"ALERT-{datetime.now().strftime('%H%M%S')}"
    
    # Chuẩn hóa level
    level_upper = level.upper().replace("CODE_", "")
    if level_upper not in ["RED", "BLUE", "YELLOW", "GREEN"]:
        level_upper = "RED"  # Default to RED for safety
    
    code = f"CODE_{level_upper}"
    description = TriageCode.get_description(code)
    
    alert_msg = (
        f"[{code}] CẢNH BÁO KHẨN CẤP ĐÃ GỬI\n"
        f"ID: {alert_id}\n"
        f"Thời gian: {timestamp}\n"
        f"Mức độ: {description}\n"
        f"Vị trí: {location}\n"
        f"Bệnh nhân: {patient_info}\n"
    )
    
    if vitals:
        alert_msg += f"Chỉ số sinh hiệu: {vitals}\n"
    
    alert_msg += "Trạng thái: Đội y tế đang được điều phối."
    
    return alert_msg


@tool
def assess_vital_signs(
    systolic_bp: Optional[int] = None,
    diastolic_bp: Optional[int] = None,
    heart_rate: Optional[int] = None,
    spo2: Optional[int] = None,
    temperature: Optional[float] = None,
    respiratory_rate: Optional[int] = None
) -> str:
    """
    Đánh giá các chỉ số sinh hiệu và trả về mã phân loại triage phù hợp.
    
    Args:
        systolic_bp: Huyết áp tâm thu (mmHg).
        diastolic_bp: Huyết áp tâm trương (mmHg).
        heart_rate: Nhịp tim (bpm).
        spo2: Độ bão hòa oxy (%).
        temperature: Nhiệt độ cơ thể (°C).
        respiratory_rate: Nhịp thở (lần/phút).
    
    Returns:
        Đánh giá với mã phân loại triage.
    """
    alerts = []
    code = TriageCode.GREEN  # Default
    
    # Đánh giá huyết áp
    if systolic_bp:
        if systolic_bp > 180 or systolic_bp < 90:
            alerts.append(f"Huyết áp tâm thu: {systolic_bp} mmHg - BẤT THƯỜNG NGHIÊM TRỌNG")
            code = TriageCode.RED
        elif systolic_bp > 140:
            alerts.append(f"Huyết áp tâm thu: {systolic_bp} mmHg - Tăng")
            if code != TriageCode.RED:
                code = TriageCode.YELLOW
    
    # Đánh giá nhịp tim
    if heart_rate:
        if heart_rate > 120 or heart_rate < 50:
            alerts.append(f"Nhịp tim: {heart_rate} bpm - BẤT THƯỜNG NGHIÊM TRỌNG")
            code = TriageCode.RED
        elif heart_rate > 100:
            alerts.append(f"Nhịp tim: {heart_rate} bpm - Nhanh")
            if code != TriageCode.RED:
                code = TriageCode.YELLOW
    
    # Đánh giá SpO2
    if spo2:
        if spo2 < 92:
            alerts.append(f"SpO2: {spo2}% - THIẾU OXY NGHIÊM TRỌNG")
            code = TriageCode.RED
        elif spo2 < 95:
            alerts.append(f"SpO2: {spo2}% - Thấp")
            if code != TriageCode.RED:
                code = TriageCode.YELLOW
    
    # Đánh giá nhiệt độ
    if temperature:
        if temperature > 40 or temperature < 35:
            alerts.append(f"Nhiệt độ: {temperature}°C - BẤT THƯỜNG")
            if code not in [TriageCode.RED, TriageCode.BLUE]:
                code = TriageCode.YELLOW
        elif temperature > 38:
            alerts.append(f"Nhiệt độ: {temperature}°C - Sốt")
    
    # Đánh giá nhịp thở
    if respiratory_rate:
        if respiratory_rate > 30 or respiratory_rate < 10:
            alerts.append(f"Nhịp thở: {respiratory_rate} lần/phút - BẤT THƯỜNG NGHIÊM TRỌNG")
            code = TriageCode.RED
    
    # Xây dựng kết quả
    result = f"[{code}] ĐÁNH GIÁ CHỈ SỐ SINH HIỆU\n\n"
    
    if alerts:
        result += "CHỈ SỐ BẤT THƯỜNG:\n"
        for alert in alerts:
            result += f"- {alert}\n"
    else:
        result += "Các chỉ số sinh hiệu trong giới hạn bình thường.\n"
    
    # Thêm khuyến nghị
    recommendations = {
        TriageCode.RED: "HÀNH ĐỘNG: Chuyển ngay đến Khoa Cấp Cứu. Thời gian xử lý dưới 10 phút.",
        TriageCode.YELLOW: "HÀNH ĐỘNG: Ưu tiên khám trong vòng 60 phút.",
        TriageCode.GREEN: "HÀNH ĐỘNG: Khám theo thứ tự bình thường.",
        TriageCode.BLUE: "HÀNH ĐỘNG: HỒI SỨC CẤP CỨU NGAY LẬP TỨC!"
    }
    
    result += f"\n{recommendations.get(code, '')}"
    
    return result