# apps/ai_engine/graph/tools.py
"""
LangChain Tools for Medical AI Agents

Cung cấp các công cụ (tools) cho agents sử dụng, kết nối trực tiếp với Business Services.
"""

from langchain_core.tools import tool
from typing import List, Optional, Dict
from datetime import datetime
import json

# Import Services
from apps.core_services.reception.services import ReceptionService
from apps.medical_services.emr.services import ClinicalService
from apps.medical_services.paraclinical.services import OrderingService
from apps.medical_services.pharmacy.services import PharmacyService

# Import Models for lookups
from apps.core_services.core.models import ICD10Code
from apps.medical_services.paraclinical.models import ServiceResult, ServiceOrder

# ==============================================================================
# TOOLS FOR CLINICAL AGENT
# ==============================================================================

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

# ==============================================================================
# TOOLS FOR PARACLINICAL AGENT
# ==============================================================================

@tool
def order_lab_test(visit_id: str, service_ids: List[str], requester_id: str) -> str:
    """
    Tạo chỉ định xét nghiệm hoặc chẩn đoán hình ảnh.
    
    Args:
        visit_id: ID lượt khám.
        service_ids: Danh sách ID của dịch vụ cần chỉ định.
        requester_id: ID bác sĩ chỉ định (Staff ID).
    
    Returns:
        Thông báo xác nhận chỉ định.
    """
    try:
        orders = OrderingService.create_lab_order(visit_id, service_ids, requester_id)
        names = [o.service.name for o in orders]
        return f"Đã chỉ định thành công: {', '.join(names)}"
    except Exception as e:
        return f"Lỗi khi tạo chỉ định: {str(e)}"

@tool
def get_lab_results(visit_id: str) -> str:
    """
    Lấy danh sách kết quả cận lâm sàng của lượt khám hiện tại.
    
    Args:
        visit_id: ID lượt khám.
    
    Returns:
        Danh sách kết quả (tên dịch vụ, kết quả, link ảnh nếu có).
    """
    results = ServiceResult.objects.filter(
        order__visit__id=visit_id,
        order__status=ServiceOrder.Status.COMPLETED
    ).select_related('order__service')
    
    if not results:
        return "Chưa có kết quả cận lâm sàng nào cho lượt khám này."
    
    output = "KẾT QUẢ CẬN LÂM SÀNG:\n"
    for res in results:
        val = res.text_result or "Xem ảnh đính kèm"
        output += f"- {res.order.service.name}: {val}"
        if res.image_url:
            output += f" (Link: {res.image_url})"
        output += "\n"
        
    return output

# ==============================================================================
# TOOLS FOR PHARMACIST AGENT
# ==============================================================================

@tool
def check_drug_availability(medication_ids: List[str]) -> str:
    """
    Kiểm tra tồn kho thuốc.
    
    Args:
        medication_ids: Danh sách ID thuốc.
    
    Returns:
        Thông tin tồn kho cho từng thuốc.
    """
    stock = PharmacyService.check_inventory(medication_ids)
    output = "TÌNH TRẠNG KHO DƯỢC:\n"
    for name, count in stock.items():
        status = "Còn hàng" if count > 0 else "HẾT HÀNG"
        output += f"- {name}: {count} ({status})\n"
    return output

@tool
def check_drug_interaction(medication_ids: List[str]) -> str:
    """
    Kiểm tra tương tác thuốc.
    
    Args:
        medication_ids: Danh sách ID thuốc trong đơn.
    
    Returns:
        Cảnh báo tương tác nếu có.
    """
    warnings = PharmacyService.validate_interactions(medication_ids)
    if not warnings:
        return "Không phát hiện tương tác thuốc đáng kể."
    
    return "CẢNH BÁO TƯƠNG TÁC THUỐC:\n" + "\n".join(f"- {w}" for w in warnings)

# ==============================================================================
# TOOLS FOR TRIAGE AGENT (Keep relevant parts from original logic)
# ==============================================================================

@tool
def trigger_emergency_alert(level: str, location: str, patient_info: str) -> str:
    """
    Gửi cảnh báo khẩn cấp (CODE RED/BLUE).
    Hiện tại ghi log, tương lai sẽ đẩy WebSocket.
    """
    return f"[MOCK ALERT] Cảnh báo {level} tại {location} cho {patient_info} đã được gửi!"

@tool
def assess_vital_signs(
    systolic_bp: Optional[int] = None,
    heart_rate: Optional[int] = None,
    spo2: Optional[int] = None,
    temperature: Optional[float] = None
) -> str:
    """
    Đánh giá nhanh chỉ số sinh hiệu.
    """
    alerts = []
    if systolic_bp and (systolic_bp > 160 or systolic_bp < 90):
        alerts.append(f"HA: {systolic_bp} (Nguy hiểm)")
    if heart_rate and (heart_rate > 120 or heart_rate < 50):
        alerts.append(f"Mạch: {heart_rate} (Nguy hiểm)")
    if spo2 and spo2 < 92:
        alerts.append(f"SpO2: {spo2}% (Thiếu oxy)")
    
    if alerts:
        return "CẢNH BÁO SINH HIỆU: " + ", ".join(alerts)
    return "Sinh hiệu trong giới hạn an toàn."

# ==============================================================================
# TOOLS FOR CONSULTANT (Keep minimal)
# ==============================================================================

@tool
def check_appointment_slots(department: str, date: str) -> str:
    """
    Kiểm tra lịch trống (Mock).
    """
    return f"Khoa {department} ngày {date} còn trống các khung giờ: 08:00, 10:00, 14:00."
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


# ==============================================================================
# CODE CONSTANTS FOR PARACLINICAL
# ==============================================================================

class CriticalValueCode:
    """Mã cảnh báo giá trị nguy kịch xét nghiệm."""
    CRITICAL_HIGH = "CRITICAL_HIGH"
    CRITICAL_LOW = "CRITICAL_LOW"
    PANIC = "PANIC_VALUE"
    NORMAL = "NORMAL_VALUE"

    @classmethod
    def get_description(cls, code: str) -> str:
        descriptions = {
            cls.CRITICAL_HIGH: "Giá trị CAO nguy kịch - Cần can thiệp y khoa NGAY",
            cls.CRITICAL_LOW: "Giá trị THẤP nguy kịch - Cần can thiệp y khoa NGAY",
            cls.PANIC: "Giá trị HOẢNG LOẠN - Đe dọa tính mạng - BÁO ĐỘNG KHẨN CẤP",
            cls.NORMAL: "Giá trị trong giới hạn bình thường"
        }
        return descriptions.get(code, "Không xác định")


class SampleStatus:
    """Trạng thái mẫu xét nghiệm trong quy trình Lab."""
    ORDERED = "SAMPLE_ORDERED"
    COLLECTED = "SAMPLE_COLLECTED"
    RECEIVED = "SAMPLE_RECEIVED"
    PROCESSING = "SAMPLE_PROCESSING"
    COMPLETED = "SAMPLE_COMPLETED"
    VERIFIED = "SAMPLE_VERIFIED"

    @classmethod
    def get_description(cls, status: str) -> str:
        descriptions = {
            cls.ORDERED: "Đã có y lệnh - Chờ lấy mẫu",
            cls.COLLECTED: "Đã lấy mẫu - Đang vận chuyển đến Lab",
            cls.RECEIVED: "Lab đã nhận mẫu - Chờ xử lý",
            cls.PROCESSING: "Đang xử lý trong phòng Lab",
            cls.COMPLETED: "Có kết quả - Chờ xác nhận",
            cls.VERIFIED: "Kết quả đã được xác nhận"
        }
        return descriptions.get(status, "Không xác định")


class OrderStatus:
    """Trạng thái y lệnh cận lâm sàng."""
    PENDING = "ORDER_PENDING"
    APPROVED = "ORDER_APPROVED"
    REJECTED = "ORDER_REJECTED"
    IN_PROGRESS = "ORDER_IN_PROGRESS"
    COMPLETED = "ORDER_COMPLETED"


# ==============================================================================
# TOOLS FOR PARACLINICAL (ĐIỀU PHỐI VIÊN CẬN LÂM SÀNG)
# ==============================================================================

@tool
def receive_clinical_order(order_type: str, patient_id: str, order_details: str) -> str:
    """
    Nhận và xác thực y lệnh xét nghiệm/chẩn đoán hình ảnh từ Clinical Agent.
    Sử dụng khi bác sĩ chỉ định xét nghiệm hoặc chụp chiếu cho bệnh nhân.
    
    Args:
        order_type: Loại y lệnh (ví dụ: "Lab Test", "CT Scan", "MRI", "X-Ray", "Ultrasound").
        patient_id: Mã bệnh nhân.
        order_details: Chi tiết y lệnh (ví dụ: "CBC, BMP, Liver Function Test").
    
    Returns:
        Xác nhận tiếp nhận y lệnh với mã và trạng thái.
    """
    # TODO: Kết nối với Order Management System
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return (
        f"[{OrderStatus.PENDING}] Y LỆNH ĐÃ ĐƯỢC TIẾP NHẬN\n\n"
        f"Mã y lệnh: {order_id}\n"
        f"Thời gian: {timestamp}\n"
        f"Bệnh nhân: {patient_id}\n"
        f"Loại: {order_type}\n"
        f"Chi tiết: {order_details}\n\n"
        f"TRẠNG THÁI: Chờ kiểm tra chống chỉ định trước khi duyệt.\n"
        f"Sử dụng tool `check_contraindications` để kiểm tra an toàn."
    )


@tool
def check_contraindications(patient_id: str, procedure_type: str) -> str:
    """
    Kiểm tra chống chỉ định cho thủ thuật/xét nghiệm cụ thể.
    Sử dụng TRƯỚC KHI duyệt y lệnh để đảm bảo an toàn bệnh nhân.
    
    Args:
        patient_id: Mã bệnh nhân.
        procedure_type: Loại thủ thuật (ví dụ: "CT with contrast", "MRI", "Iodine contrast").
    
    Returns:
        Kết quả kiểm tra chống chỉ định với khuyến nghị.
    """
    # TODO: Kết nối với EMR để lấy tiền sử bệnh nhân
    procedure_lower = procedure_type.lower()
    
    # Mock logic cho các chống chỉ định thường gặp
    if "contrast" in procedure_lower or "cản quang" in procedure_lower:
        return (
            f"[ORDER_PENDING] KIỂM TRA CHỐNG CHỈ ĐỊNH - THUỐC CẢN QUANG\n\n"
            f"Bệnh nhân: {patient_id}\n"
            f"Thủ thuật: {procedure_type}\n\n"
            f"CHECKLIST KIỂM TRA:\n"
            f"□ Tiền sử dị ứng thuốc cản quang\n"
            f"□ Chức năng thận (eGFR > 30 mL/min/1.73m²)\n"
            f"□ Đang dùng Metformin (ngưng 48h trước)\n"
            f"□ Cường giáp chưa kiểm soát\n"
            f"□ Đa u tủy xương (Multiple Myeloma)\n\n"
            f"CHỜ XÁC NHẬN: Kiểm tra eGFR trước khi duyệt y lệnh."
        )
    
    if "mri" in procedure_lower:
        return (
            f"[ORDER_PENDING] KIỂM TRA CHỐNG CHỈ ĐỊNH - MRI\n\n"
            f"Bệnh nhân: {patient_id}\n"
            f"Thủ thuật: {procedure_type}\n\n"
            f"CHECKLIST KIỂM TRA:\n"
            f"□ Máy tạo nhịp tim (Pacemaker)\n"
            f"□ Implant kim loại (cochlear, clip phình mạch)\n"
            f"□ Mảnh kim loại trong cơ thể\n"
            f"□ Thai kỳ tam cá nguyệt đầu\n\n"
            f"KHUYẾN NGHỊ: Hoàn thành bảng câu hỏi an toàn MRI trước khi tiến hành."
        )
    
    return (
        f"[{OrderStatus.APPROVED}] KHÔNG CÓ CHỐNG CHỈ ĐỊNH\n\n"
        f"Bệnh nhân: {patient_id}\n"
        f"Thủ thuật: {procedure_type}\n\n"
        f"Kết quả: Không phát hiện chống chỉ định rõ ràng.\n"
        f"Y lệnh có thể được duyệt và thực hiện."
    )


@tool
def track_sample_status(sample_id: str) -> str:
    """
    Theo dõi trạng thái mẫu xét nghiệm trong quy trình Lab.
    Sử dụng để kiểm tra mẫu đã lấy chưa, đã vào Lab chưa, khi nào có kết quả.
    
    Args:
        sample_id: Mã mẫu xét nghiệm (ví dụ: "XN-2026-0129-001").
    
    Returns:
        Thông tin trạng thái hiện tại và timeline của mẫu.
    """
    # TODO: Kết nối với LIS (Laboratory Information System)
    timestamp = datetime.now().strftime("%H:%M")
    
    # Mock random status for demo
    import random
    statuses = [
        (SampleStatus.ORDERED, "08:30", "Y lệnh được tạo"),
        (SampleStatus.COLLECTED, "08:45", "Điều dưỡng lấy mẫu tại giường"),
        (SampleStatus.RECEIVED, "09:00", "Lab Huyết học nhận mẫu"),
        (SampleStatus.PROCESSING, "09:15", "Đang xử lý trên máy phân tích"),
    ]
    
    current_index = random.randint(0, len(statuses) - 1)
    current_status = statuses[current_index]
    
    result = f"[{current_status[0]}] TRẠNG THÁI MẪU XÉT NGHIỆM\n\n"
    result += f"Mã mẫu: {sample_id}\n\n"
    result += "TIMELINE:\n"
    
    for i, (status, time, desc) in enumerate(statuses):
        if i <= current_index:
            result += f"✓ {time} - [{status}] {desc}\n"
        else:
            result += f"○ Chờ - [{status}] {desc}\n"
    
    if current_index < len(statuses) - 1:
        result += f"\nDỰ KIẾN HOÀN THÀNH: {timestamp.split(':')[0]}:45"
    else:
        result += f"\nDỰ KIẾN CÓ KẾT QUẢ: 15-30 phút"
    
    return result


@tool
def check_critical_values(test_type: str, value: float, unit: str) -> str:
    """
    Kiểm tra xem giá trị xét nghiệm có vượt ngưỡng nguy kịch không.
    Sử dụng ngay khi có kết quả xét nghiệm để phát hiện giá trị cần can thiệp khẩn.
    
    Args:
        test_type: Loại xét nghiệm (ví dụ: "Glucose", "Potassium", "Hemoglobin").
        value: Giá trị kết quả.
        unit: Đơn vị (ví dụ: "mg/dL", "mEq/L", "g/dL").
    
    Returns:
        Đánh giá mức độ nguy kịch và hành động cần thiết.
    """
    # Critical value thresholds
    critical_ranges = {
        "glucose": {"low": 40, "high": 400, "unit": "mg/dL", "name": "Glucose"},
        "potassium": {"low": 2.5, "high": 6.5, "unit": "mEq/L", "name": "Potassium (K+)"},
        "sodium": {"low": 120, "high": 160, "unit": "mEq/L", "name": "Sodium (Na+)"},
        "hemoglobin": {"low": 7.0, "high": 20.0, "unit": "g/dL", "name": "Hemoglobin"},
        "platelet": {"low": 20, "high": 1000, "unit": "x10³/µL", "name": "Platelet"},
        "troponin": {"low": None, "high": 0.4, "unit": "ng/mL", "name": "Troponin I"},
        "inr": {"low": None, "high": 5.0, "unit": "", "name": "INR"},
        "creatinine": {"low": None, "high": 10.0, "unit": "mg/dL", "name": "Creatinine"},
    }
    
    test_lower = test_type.lower()
    
    if test_lower in critical_ranges:
        range_info = critical_ranges[test_lower]
        
        # Check panic values
        if range_info["low"] and value < range_info["low"]:
            code = CriticalValueCode.PANIC if value < range_info["low"] * 0.5 else CriticalValueCode.CRITICAL_LOW
            return (
                f"[{code}] CẢNH BÁO GIÁ TRỊ NGUY KỊCH\n\n"
                f"Xét nghiệm: {range_info['name']}\n"
                f"Kết quả: {value} {unit}\n"
                f"Ngưỡng nguy kịch thấp: < {range_info['low']} {range_info['unit']}\n\n"
                f"TÌNH TRẠNG: {CriticalValueCode.get_description(code)}\n\n"
                f"HÀNH ĐỘNG NGAY:\n"
                f"1. Thông báo bác sĩ điều trị NGAY LẬP TỨC\n"
                f"2. Chuẩn bị can thiệp y khoa khẩn cấp\n"
                f"3. Xem xét nhập Khoa Cấp cứu/ICU"
            )
        
        if range_info["high"] and value > range_info["high"]:
            code = CriticalValueCode.PANIC if value > range_info["high"] * 1.5 else CriticalValueCode.CRITICAL_HIGH
            return (
                f"[{code}] CẢNH BÁO GIÁ TRỊ NGUY KỊCH\n\n"
                f"Xét nghiệm: {range_info['name']}\n"
                f"Kết quả: {value} {unit}\n"
                f"Ngưỡng nguy kịch cao: > {range_info['high']} {range_info['unit']}\n\n"
                f"TÌNH TRẠNG: {CriticalValueCode.get_description(code)}\n\n"
                f"HÀNH ĐỘNG NGAY:\n"
                f"1. Thông báo bác sĩ điều trị NGAY LẬP TỨC\n"
                f"2. Chuẩn bị can thiệp y khoa khẩn cấp\n"
                f"3. Xem xét nhập Khoa Cấp cứu/ICU"
            )
    
    return (
        f"[{CriticalValueCode.NORMAL}] GIÁ TRỊ BÌNH THƯỜNG\n\n"
        f"Xét nghiệm: {test_type}\n"
        f"Kết quả: {value} {unit}\n\n"
        f"ĐÁNH GIÁ: Giá trị trong giới hạn bình thường, không cần can thiệp khẩn cấp."
    )


@tool
def analyze_trend(patient_id: str, test_type: str, days: int = 30) -> str:
    """
    Phân tích xu hướng kết quả xét nghiệm theo thời gian.
    So sánh kết quả hiện tại với các kết quả trước để đưa ra nhận định.
    
    Args:
        patient_id: Mã bệnh nhân.
        test_type: Loại xét nghiệm cần phân tích xu hướng.
        days: Số ngày lịch sử cần xem xét (mặc định 30 ngày).
    
    Returns:
        Phân tích xu hướng với biểu đồ giá trị theo thời gian.
    """
    # TODO: Kết nối với LIS để lấy lịch sử kết quả
    
    # Mock data for demo
    test_lower = test_type.lower()
    
    if "hba1c" in test_lower or "hemoglobin a1c" in test_lower:
        return (
            f"[TREND_ANALYSIS] PHÂN TÍCH XU HƯỚNG HbA1c\n\n"
            f"Bệnh nhân: {patient_id}\n"
            f"Khoảng thời gian: {days} ngày gần nhất\n\n"
            f"| Ngày | Kết quả | Đánh giá |\n"
            f"|------|---------|----------|\n"
            f"| 01-11-2025 | 8.5% | Kiểm soát kém |\n"
            f"| 01-12-2025 | 8.0% | Cải thiện nhẹ |\n"
            f"| 01-01-2026 | 7.5% | Đang tiến triển |\n"
            f"| 29-01-2026 | 7.2% | Gần mục tiêu |\n\n"
            f"XU HƯỚNG: ↓ Giảm đều (-1.3% trong 3 tháng)\n"
            f"ĐÁNH GIÁ: Kiểm soát đường huyết CẢI THIỆN TỐT\n"
            f"MỤC TIÊU: < 7.0% cho bệnh nhân đái tháo đường\n\n"
            f"KHUYẾN NGHỊ: Tiếp tục phác đồ hiện tại. Tái kiểm tra sau 3 tháng."
        )
    
    if "creatinine" in test_lower:
        return (
            f"[TREND_ANALYSIS] PHÂN TÍCH XU HƯỚNG CREATININE\n\n"
            f"Bệnh nhân: {patient_id}\n"
            f"Khoảng thời gian: {days} ngày gần nhất\n\n"
            f"| Ngày | Creatinine | eGFR | Giai đoạn CKD |\n"
            f"|------|------------|------|---------------|\n"
            f"| 01-12-2025 | 1.2 mg/dL | 68 | Stage 2 |\n"
            f"| 15-12-2025 | 1.4 mg/dL | 58 | Stage 3a |\n"
            f"| 01-01-2026 | 1.6 mg/dL | 48 | Stage 3a |\n"
            f"| 29-01-2026 | 1.8 mg/dL | 42 | Stage 3b |\n\n"
            f"XU HƯỚNG: ↑ TĂNG đáng kể (+0.6 mg/dL trong 2 tháng)\n"
            f"ĐÁNH GIÁ: Chức năng thận GIẢM - Cần theo dõi chặt\n\n"
            f"CẢNH BÁO: Tiến triển CKD. Cần:\n"
            f"1. Xem xét điều chỉnh thuốc độc thận\n"
            f"2. Tham vấn chuyên khoa Thận"
        )
    
    return (
        f"[TREND_ANALYSIS] PHÂN TÍCH XU HƯỚNG\n\n"
        f"Bệnh nhân: {patient_id}\n"
        f"Xét nghiệm: {test_type}\n"
        f"Khoảng thời gian: {days} ngày\n\n"
        f"Không có đủ dữ liệu lịch sử để phân tích xu hướng.\n"
        f"Cần ít nhất 2 kết quả trong khoảng thời gian yêu cầu."
    )


@tool
def normalize_lab_result(raw_data: str, machine_type: str) -> str:
    """
    Chuẩn hóa kết quả xét nghiệm thô từ máy thành định dạng chuẩn.
    Sử dụng để chuyển đổi output từ các máy xét nghiệm khác nhau.
    
    Args:
        raw_data: Dữ liệu thô từ máy xét nghiệm.
        machine_type: Loại máy (ví dụ: "Sysmex", "Roche", "Abbott").
    
    Returns:
        Kết quả đã được chuẩn hóa theo định dạng chuẩn.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return (
        f"[DATA_NORMALIZED] KẾT QUẢ ĐÃ CHUẨN HÓA\n\n"
        f"Nguồn: Máy {machine_type}\n"
        f"Thời gian xử lý: {timestamp}\n\n"
        f"DỮ LIỆU GỐC:\n{raw_data}\n\n"
        f"ĐỊNH DẠNG CHUẨN:\n"
        f"| Chỉ số | Kết quả | Đơn vị | Tham chiếu | Đánh giá |\n"
        f"|--------|---------|--------|------------|----------|\n"
        f"| (Đã được chuẩn hóa từ dữ liệu thô) |\n\n"
        f"Kết quả này có thể được đọc bởi các Agent khác trong hệ thống."
    )


@tool
def extract_imaging_conclusions(report_text: str) -> str:
    """
    Trích xuất kết luận chính từ báo cáo chẩn đoán hình ảnh dài.
    Sử dụng để tóm tắt báo cáo X-Ray, CT, MRI, Siêu âm cho agent khác.
    
    Args:
        report_text: Văn bản đầy đủ của báo cáo chẩn đoán hình ảnh.
    
    Returns:
        Tóm tắt kết luận chính, phát hiện bất thường và khuyến nghị.
    """
    # Simple keyword-based extraction for demo
    report_lower = report_text.lower()
    
    findings = []
    if "mass" in report_lower or "u" in report_lower or "khối" in report_lower:
        findings.append("Phát hiện khối/u cần đánh giá thêm")
    if "fracture" in report_lower or "gãy" in report_lower:
        findings.append("Có dấu hiệu gãy xương")
    if "pneumonia" in report_lower or "viêm phổi" in report_lower:
        findings.append("Hình ảnh viêm phổi")
    if "normal" in report_lower or "bình thường" in report_lower:
        findings.append("Các cấu trúc khảo sát trong giới hạn bình thường")
    
    if not findings:
        findings.append("Xem báo cáo gốc để biết chi tiết")
    
    return (
        f"[IMAGING_SUMMARY] TÓM TẮT CHẨN ĐOÁN HÌNH ẢNH\n\n"
        f"BÁO CÁO GỐC (trích):\n"
        f"{report_text[:200]}{'...' if len(report_text) > 200 else ''}\n\n"
        f"KẾT LUẬN CHÍNH:\n"
        + "\n".join(f"• {f}" for f in findings) +
        f"\n\nLƯU Ý: Đây là tóm tắt tự động. Bác sĩ cần đọc báo cáo gốc để ra quyết định lâm sàng."
    )