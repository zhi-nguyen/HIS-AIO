# apps/ai_engine/agents/schemas.py
"""
Pydantic Schemas for Agent Structured Output

Định nghĩa các schema bắt buộc để đảm bảo tất cả agents
trả về JSON với thinking_progress field để tránh hallucination.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# =============================================================================
# BASE RESPONSE SCHEMA
# =============================================================================

class BaseAgentResponse(BaseModel):
    """
    Base schema cho tất cả agents.
    
    Attributes:
        thinking_progress: BẮT BUỘC - Từng bước suy nghĩ của agent
        final_response: Phản hồi chính gửi cho user
        confidence_score: Độ tin cậy của phản hồi (0.0 - 1.0)
    """
    thinking_progress: List[str] = Field(
        ...,
        min_length=1,
        description="Từng bước suy nghĩ của agent, BẮT BUỘC có ít nhất 1 bước"
    )
    final_response: str = Field(
        ...,
        min_length=1,
        description="Phản hồi chính gửi cho user bằng tiếng Việt"
    )
    confidence_score: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Độ tin cậy của phản hồi, từ 0.0 đến 1.0"
    )


# =============================================================================
# CLINICAL AGENT RESPONSE
# =============================================================================

class ClinicalResponse(BaseAgentResponse):
    """Response schema cho Clinical Agent (Bác sĩ chẩn đoán)."""
    
    symptom_analysis: Optional[str] = Field(
        default=None,
        description="Phân tích triệu chứng bệnh nhân"
    )
    differential_diagnosis: Optional[List[str]] = Field(
        default=None,
        description="Danh sách chẩn đoán phân biệt"
    )
    recommended_tests: Optional[List[str]] = Field(
        default=None,
        description="Các xét nghiệm đề xuất"
    )
    requires_urgent_care: bool = Field(
        default=False,
        description="Có cần cấp cứu không"
    )


# =============================================================================
# TRIAGE AGENT RESPONSE
# =============================================================================

class TriageResponse(BaseAgentResponse):
    """Response schema cho Triage Agent (Điều dưỡng phân luồng)."""
    
    triage_code: Literal["CODE_BLUE", "CODE_RED", "CODE_YELLOW", "CODE_GREEN"] = Field(
        ...,
        description="Mã phân loại cấp cứu"
    )
    vital_signs_analysis: Optional[str] = Field(
        default=None,
        description="Phân tích các chỉ số sinh hiệu"
    )
    recommended_department: Optional[str] = Field(
        default=None,
        description="Khoa phòng khuyến nghị chuyển đến"
    )
    time_to_treatment: Optional[str] = Field(
        default=None,
        description="Thời gian cần xử lý (VD: 'Dưới 10 phút')"
    )
    trigger_alert: bool = Field(
        default=False,
        description="Có cần kích hoạt cảnh báo khẩn cấp không"
    )


# =============================================================================
# PHARMACIST AGENT RESPONSE
# =============================================================================

class DrugInteraction(BaseModel):
    """Chi tiết tương tác thuốc."""
    drug_pair: str = Field(..., description="Cặp thuốc tương tác")
    severity: Literal["SEVERITY_MAJOR", "SEVERITY_MODERATE", "SEVERITY_MINOR"] = Field(
        ..., description="Mức độ nghiêm trọng"
    )
    description: str = Field(..., description="Mô tả tương tác")
    recommendation: str = Field(..., description="Khuyến nghị xử lý")


class PharmacistResponse(BaseAgentResponse):
    """Response schema cho Pharmacist Agent (Dược sĩ lâm sàng)."""
    
    drug_interactions: Optional[List[DrugInteraction]] = Field(
        default=None,
        description="Danh sách tương tác thuốc phát hiện được"
    )
    alternative_drugs: Optional[List[str]] = Field(
        default=None,
        description="Các thuốc thay thế đề xuất"
    )
    dosage_guidance: Optional[str] = Field(
        default=None,
        description="Hướng dẫn liều dùng"
    )
    contraindication_warning: Optional[str] = Field(
        default=None,
        description="Cảnh báo chống chỉ định"
    )


# =============================================================================
# PARACLINICAL AGENT RESPONSE
# =============================================================================

class CriticalValue(BaseModel):
    """Chi tiết giá trị nguy kịch."""
    test_name: str = Field(..., description="Tên xét nghiệm")
    value: str = Field(..., description="Giá trị đo được")
    unit: str = Field(..., description="Đơn vị")
    normal_range: str = Field(..., description="Khoảng bình thường")
    status: Literal["CRITICAL_HIGH", "CRITICAL_LOW", "PANIC_VALUE", "NORMAL_VALUE"] = Field(
        ..., description="Trạng thái"
    )


class ParaclinicalResponse(BaseAgentResponse):
    """Response schema cho Paraclinical Agent (Điều phối viên cận lâm sàng)."""
    
    order_status: Optional[Literal[
        "ORDER_PENDING", "ORDER_APPROVED", "ORDER_REJECTED", 
        "ORDER_IN_PROGRESS", "ORDER_COMPLETED"
    ]] = Field(default=None, description="Trạng thái y lệnh")
    
    critical_values: Optional[List[CriticalValue]] = Field(
        default=None,
        description="Các giá trị nguy kịch phát hiện được"
    )
    contraindication_found: bool = Field(
        default=False,
        description="Có phát hiện chống chỉ định không"
    )
    contraindication_details: Optional[str] = Field(
        default=None,
        description="Chi tiết chống chỉ định"
    )
    trend_analysis: Optional[str] = Field(
        default=None,
        description="Phân tích xu hướng kết quả"
    )
    trigger_critical_alert: bool = Field(
        default=False,
        description="Có cần gửi cảnh báo giá trị nguy kịch không"
    )


# =============================================================================
# CONSULTANT AGENT RESPONSE
# =============================================================================

class AppointmentInfo(BaseModel):
    """Thông tin lịch hẹn."""
    department: str = Field(..., description="Khoa phòng")
    date: str = Field(..., description="Ngày hẹn")
    time_slot: str = Field(..., description="Giờ hẹn")
    doctor_name: Optional[str] = Field(default=None, description="Tên bác sĩ")


class ConsultantResponse(BaseAgentResponse):
    """Response schema cho Consultant Agent (Nhân viên tư vấn)."""
    
    appointment_info: Optional[AppointmentInfo] = Field(
        default=None,
        description="Thông tin lịch hẹn được đặt"
    )
    available_slots: Optional[List[str]] = Field(
        default=None,
        description="Các slot còn trống"
    )
    department_info: Optional[str] = Field(
        default=None,
        description="Thông tin khoa phòng"
    )
    insurance_guidance: Optional[str] = Field(
        default=None,
        description="Hướng dẫn về bảo hiểm"
    )


# =============================================================================
# SUMMARIZE AGENT RESPONSE
# =============================================================================

class SummarizeResponse(BaseAgentResponse):
    """Response schema cho Summarize Agent (Tóm tắt bệnh án)."""
    
    patient_info: Optional[str] = Field(
        default=None,
        description="Thông tin cơ bản bệnh nhân"
    )
    primary_diagnosis: Optional[str] = Field(
        default=None,
        description="Chẩn đoán chính"
    )
    medical_history: Optional[str] = Field(
        default=None,
        description="Tiền sử quan trọng"
    )
    current_medications: Optional[List[str]] = Field(
        default=None,
        description="Thuốc đang dùng"
    )
    recent_updates: Optional[str] = Field(
        default=None,
        description="Diễn biến gần đây"
    )
    special_notes: Optional[str] = Field(
        default=None,
        description="Lưu ý đặc biệt"
    )


# =============================================================================
# MARKETING AGENT RESPONSE
# =============================================================================

class MarketingResponse(BaseAgentResponse):
    """Response schema cho Marketing Agent (Marketing y tế)."""
    
    content_type: Optional[Literal[
        "social_media", "email", "article", "promotion", "health_tip"
    ]] = Field(default=None, description="Loại nội dung")
    
    headline: Optional[str] = Field(
        default=None,
        description="Tiêu đề nội dung"
    )
    body_content: Optional[str] = Field(
        default=None,
        description="Nội dung chính"
    )
    call_to_action: Optional[str] = Field(
        default=None,
        description="Kêu gọi hành động"
    )
    target_audience: Optional[str] = Field(
        default=None,
        description="Đối tượng mục tiêu"
    )


# =============================================================================
# SUPERVISOR/ROUTER RESPONSE (Already exists, adding thinking)
# =============================================================================

class SupervisorResponse(BaseModel):
    """Response schema cho Supervisor (Điều phối viên)."""
    
    thinking_progress: List[str] = Field(
        ...,
        min_length=1,
        description="Phân tích ngữ cảnh và ý định người dùng"
    )
    next_agent: Literal[
        "CONSULTANT", "TRIAGE", "CLINICAL", "PHARMACIST", 
        "PARACLINICAL", "SUMMARIZE", "MARKETING", "HUMAN", "END"
    ] = Field(
        ...,
        description="Agent chuyên môn được chọn để xử lý yêu cầu"
    )
    routing_reason: str = Field(
        ...,
        description="Lý do chọn agent này"
    )
