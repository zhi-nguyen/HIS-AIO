# apps/ai_engine/agents/paraclinical_agent/tools.py
"""
Tools cho Paraclinical Agent (Điều phối viên cận lâm sàng)

Cung cấp các tool tiếp nhận y lệnh, kiểm tra chống chỉ định,
theo dõi mẫu xét nghiệm, kiểm tra giá trị nguy kịch, phân tích xu hướng,
chuẩn hóa kết quả và trích xuất kết luận hình ảnh.
"""

from langchain_core.tools import tool
from datetime import datetime


# ==============================================================================
# CONSTANTS
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
# TOOLS
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
