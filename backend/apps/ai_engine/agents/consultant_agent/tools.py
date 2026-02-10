# apps/ai_engine/agents/consultant_agent/tools.py
"""
Tools cho Consultant Agent (Nhân viên tư vấn / Đặt lịch)

Cung cấp các tool kiểm tra lịch trống, mở form đặt lịch, và đặt lịch hẹn khám.
"""

from langchain_core.tools import tool
from datetime import datetime
import json


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
def open_booking_form(department: str, date: str, suggested_times: str = "", patient_note: str = "") -> str:
    """
    Mở form đặt lịch trên giao diện người dùng.
    Sử dụng khi người dùng muốn đặt lịch hẹn và đã xác nhận khoa/ngày.
    
    QUAN TRỌNG: Tool này KHÔNG tự đặt lịch. Nó yêu cầu Frontend hiển thị form 
    để bệnh nhân tự điền thông tin cá nhân và xác nhận.

    QUY TRÌNH:
    1. Trước tiên gọi check_appointment_slots để kiểm tra lịch trống
    2. Sau đó gọi open_booking_form với thông tin khoa, ngày, khung giờ gợi ý
    
    Args:
        department: Tên khoa đã được xác nhận (vd: "Cardiology", "Tim mạch").
        date: Ngày đặt lịch (YYYY-MM-DD).
        suggested_times: Các khung giờ gợi ý, phân cách bởi dấu phẩy (vd: "08:00, 10:00, 14:00").
        patient_note: Ghi chú hoặc lý do khám nếu người dùng đã đề cập.
    
    Returns:
        JSON signal for frontend to render booking form.
    """
    return json.dumps({
        "__ui_action__": "open_booking_form",
        "department": department,
        "date": date,
        "suggested_times": [t.strip() for t in suggested_times.split(",") if t.strip()],
        "patient_note": patient_note,
    })


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
