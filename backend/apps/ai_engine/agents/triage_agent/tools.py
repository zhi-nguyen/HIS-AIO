# apps/ai_engine/agents/triage_agent/tools.py
"""
Tools cho Triage Agent (Điều dưỡng phân luồng)

Cung cấp các tool gửi cảnh báo khẩn cấp và đánh giá sinh hiệu.
"""

from langchain_core.tools import tool
from typing import Optional
from datetime import datetime


# ==============================================================================
# CONSTANTS
# ==============================================================================

class TriageCode:
    """Mã phân loại triage theo quy chuẩn bệnh viện."""
    BLUE = "CODE_BLUE"      # Hồi sức cấp cứu (ngừng tim)
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


# ==============================================================================
# TOOLS
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
