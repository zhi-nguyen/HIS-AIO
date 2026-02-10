# apps/core_services/appointments/booking_api.py
"""
Public Booking API for Patient Chatbot

Nhận dữ liệu form đặt lịch từ PatientChatbot frontend,
tạo bản ghi Appointment trong database.

Endpoint: POST /api/v1/appointments/book/
Permission: AllowAny (chatbot công khai, không cần auth)
"""

import logging
from datetime import datetime

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import Appointment

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_booking(request):
    """
    Tạo lịch hẹn khám từ form đặt lịch của chatbot.
    
    Request Body:
        {
            "patient_name": "Nguyễn Văn A",
            "phone": "0901234567",
            "department": "Cardiology",
            "date": "2026-02-11",
            "time": "08:00",
            "reason": "Khám tim định kỳ"
        }
    
    Response:
        {
            "success": true,
            "booking_ref": "BK-4567-1230",
            "message": "Đặt lịch thành công!"
        }
    """
    data = request.data
    
    # Validate required fields
    required_fields = ['patient_name', 'phone', 'department', 'date', 'time']
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return Response(
            {
                "success": False,
                "error": f"Thiếu thông tin bắt buộc: {', '.join(missing)}"
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Generate booking reference
        phone_suffix = data['phone'][-4:] if len(data['phone']) >= 4 else data['phone']
        time_suffix = datetime.now().strftime('%H%M')
        booking_ref = f"BK-{phone_suffix}-{time_suffix}"
        
        # TODO: Kết nối với Appointment model thực tế
        # Hiện tại cần lookup Patient và Department từ database
        # Tạm thời trả về mock response
        #
        # Khi có đầy đủ dữ liệu:
        # patient = Patient.objects.get_or_create(phone=data['phone'], defaults={...})
        # department = Department.objects.get(name__icontains=data['department'])
        # appointment = Appointment.objects.create(
        #     appointment_code=booking_ref,
        #     patient=patient,
        #     department=department,
        #     scheduled_time=f"{data['date']}T{data['time']}:00",
        #     reason_for_visit=data.get('reason', ''),
        #     status=Appointment.Status.SCHEDULED,
        # )
        
        logger.info(
            f"[BOOKING] Đặt lịch: {booking_ref} | "
            f"Bệnh nhân: {data['patient_name']} | "
            f"Khoa: {data['department']} | "
            f"Thời gian: {data['date']} {data['time']}"
        )
        
        return Response({
            "success": True,
            "booking_ref": booking_ref,
            "message": "Đặt lịch thành công!",
            "details": {
                "patient_name": data['patient_name'],
                "phone": data['phone'],
                "department": data['department'],
                "date": data['date'],
                "time": data['time'],
                "reason": data.get('reason', ''),
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"[BOOKING] Error: {e}", exc_info=True)
        return Response(
            {
                "success": False,
                "error": f"Lỗi khi đặt lịch: {str(e)}"
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
