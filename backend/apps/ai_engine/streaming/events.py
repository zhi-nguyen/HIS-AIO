"""
Streaming Event Types and Vietnamese Translations

Defines event types and human-readable status messages for the frontend.
"""

from typing import TypedDict, Optional, Any, Dict
from dataclasses import dataclass, field
from enum import Enum


class EventType:
    """Event type constants for SSE streaming."""
    STATUS = "status"
    TOKEN = "token"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    ERROR = "error"
    DONE = "done"
    KEEPALIVE = "keepalive"


class StatusType:
    """Status subtypes for status events."""
    THINKING = "thinking"
    AGENT = "agent"
    TOOL = "tool"
    PROCESSING = "processing"


# Vietnamese status messages for the frontend
# Maps internal event names to user-friendly Vietnamese messages
EVENT_MESSAGES_VI: Dict[str, str] = {
    # General status
    "thinking": "Đang suy nghĩ...",
    "processing": "Đang xử lý...",
    "connecting": "Đang kết nối...",
    
    # Agent-specific status
    "supervisor": "Đang phân tích yêu cầu...",
    "clinical": "Đang đánh giá lâm sàng...",
    "triage": "Đang phân loại mức độ ưu tiên...",
    "consultant": "Đang tư vấn...",
    "pharmacist": "Đang tra cứu dược thư...",
    "paraclinical": "Đang xem xét kết quả xét nghiệm...",
    "summarize": "Đang tổng hợp thông tin...",
    "marketing": "Đang chuẩn bị thông tin dịch vụ...",
    
    # Tool-specific status
    "rag_search": "Đang tìm kiếm thông tin y khoa...",
    "icd10_lookup": "Đang tra cứu mã ICD-10...",
    "drug_interaction": "Đang kiểm tra tương tác thuốc...",
    "lab_analysis": "Đang phân tích kết quả xét nghiệm...",
    "vital_check": "Đang đánh giá dấu hiệu sinh tồn...",
    "emr_lookup": "Đang tra cứu hồ sơ bệnh án...",
    "appointment_check": "Đang kiểm tra lịch hẹn...",
    
    # Completion status
    "done": "Hoàn thành",
    "error": "Đã xảy ra lỗi",
}


# Tool name to Vietnamese message mapping
TOOL_MESSAGES_VI: Dict[str, str] = {
    # RAG tools
    "search_medical_knowledge": "Đang tìm kiếm thông tin y khoa...",
    "search_drug_database": "Đang tra cứu thông tin thuốc...",
    "search_icd10": "Đang tra cứu mã bệnh ICD-10...",
    
    # Clinical tools
    "check_drug_interaction": "Đang kiểm tra tương tác thuốc...",
    "analyze_lab_results": "Đang phân tích kết quả xét nghiệm...",
    "check_contraindications": "Đang kiểm tra chống chỉ định...",
    
    # Paraclinical tools
    "create_lab_order": "Đang tạo phiếu xét nghiệm...",
    "track_sample_status": "Đang theo dõi trạng thái mẫu...",
    "analyze_critical_values": "Đang phân tích giá trị nguy hiểm...",
    "extract_imaging_conclusions": "Đang trích xuất kết luận hình ảnh...",
    
    # Triage tools
    "escalate_to_human": "Đang chuyển tiếp cho nhân viên y tế...",
    "request_emergency_response": "Đang yêu cầu phản hồi khẩn cấp...",
    
    # Default
    "default": "Đang xử lý...",
}


@dataclass
class StreamEvent:
    """
    Structured streaming event for SSE.
    
    Attributes:
        type: Event type (status, token, error, done)
        data: Event-specific data payload
    """
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"type": self.type}
        result.update(self.data)
        return result
    
    @classmethod
    def status(cls, status: str, message: str = None, agent: str = None) -> "StreamEvent":
        """Create a status event."""
        if message is None:
            message = EVENT_MESSAGES_VI.get(status, EVENT_MESSAGES_VI.get("processing"))
        
        data = {
            "status": status,
            "message": message,
        }
        if agent:
            data["agent"] = agent
        
        return cls(type=EventType.STATUS, data=data)
    
    @classmethod
    def token(cls, content: str) -> "StreamEvent":
        """Create a token streaming event."""
        return cls(type=EventType.TOKEN, data={"content": content})
    
    @classmethod
    def tool_start(cls, tool_name: str) -> "StreamEvent":
        """Create a tool start event."""
        message = TOOL_MESSAGES_VI.get(tool_name, TOOL_MESSAGES_VI.get("default"))
        return cls(
            type=EventType.TOOL_START,
            data={
                "tool_name": tool_name,
                "message": message,
            }
        )
    
    @classmethod
    def tool_end(cls, tool_name: str, result: Any = None) -> "StreamEvent":
        """Create a tool end event."""
        data = {"tool_name": tool_name}
        if result is not None:
            # Only include a summary, not the full result
            data["has_result"] = True
        return cls(type=EventType.TOOL_END, data=data)
    
    @classmethod
    def error(cls, message: str, code: str = "UNKNOWN_ERROR") -> "StreamEvent":
        """Create an error event."""
        return cls(
            type=EventType.ERROR,
            data={
                "message": message,
                "code": code,
            }
        )
    
    @classmethod
    def done(cls, full_response: str, metadata: Dict[str, Any] = None) -> "StreamEvent":
        """Create a completion event."""
        data = {"full_response": full_response}
        if metadata:
            data["metadata"] = metadata
        return cls(type=EventType.DONE, data=data)
    
    @classmethod
    def keepalive(cls) -> "StreamEvent":
        """Create a keepalive event to maintain SSE connection."""
        return cls(type=EventType.KEEPALIVE, data={"timestamp": None})
