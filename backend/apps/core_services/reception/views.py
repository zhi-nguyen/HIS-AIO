from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Visit
from .serializers import VisitSerializer
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)


class VisitViewSet(viewsets.ModelViewSet):
    queryset = Visit.objects.select_related(
        'patient', 'recommended_department', 'confirmed_department'
    ).all().order_by('-check_in_time')
    serializer_class = VisitSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['visit_code', 'patient__patient_code', 'patient__first_name']
    filterset_fields = ['status', 'priority', 'patient']

    def perform_create(self, serializer):
        # Auto-generate visit_code and queue_number
        today = timezone.now().date()
        today_str = timezone.now().strftime('%Y%m%d')
        
        # Calculate queue_number for today
        today_count = Visit.objects.filter(check_in_time__date=today).count()
        queue_number = today_count + 1
        
        # Generate visit_code
        code = f"V{today_str}-{uuid.uuid4().hex[:6].upper()}"
        serializer.save(
            visit_code=code, 
            check_in_time=timezone.now(),
            queue_number=queue_number
        )

    @action(detail=True, methods=['post'], url_path='triage')
    def run_triage(self, request, pk=None):
        """
        Gọi AI Agent phân luồng cho visit này.
        
        POST /reception/visits/{id}/triage/
        Body: { "chief_complaint": "Đau ngực trái..." }
        
        Trả về kết quả AI triage:
        - triage_code, recommended_department, confidence
        - ai_response (full text AI)
        """
        visit = self.get_object()
        chief_complaint = request.data.get('chief_complaint', '')
        
        if not chief_complaint:
            return Response(
                {'error': 'chief_complaint là bắt buộc'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Lấy thông tin bệnh nhân
        patient = visit.patient
        patient_name = f"{patient.last_name} {patient.first_name}"
        
        # Build structured message cho AI triage agent
        structured_message = f"""[TRIAGE_ASSESSMENT_REQUEST]
Mã bệnh nhân: {patient.patient_code}
Họ tên: {patient_name}
Giới tính: {patient.get_gender_display() if hasattr(patient, 'get_gender_display') else patient.gender}
Ngày sinh: {patient.date_of_birth}

LÝ DO KHÁM:
{chief_complaint}

YÊU CẦU: 
1. Đánh giá mức độ ưu tiên (triage code: CODE_RED/CODE_YELLOW/CODE_GREEN)
2. Đề xuất khoa phù hợp nhất (chọn 1 trong các khoa có sẵn trong bệnh viện)
3. Ước tính mức độ tin cậy (confidence) từ 0-100%
4. Giải thích ngắn gọn lý do"""

        import time
        session_id = f"triage-{visit.visit_code}-{int(time.time())}"
        
        try:
            from apps.ai_engine.streaming.service import StreamingService
            streaming_service = StreamingService()
            result = asyncio.run(streaming_service.get_full_response(
                message=structured_message,
                session_id=session_id,
                patient_context={
                    "patient_id": str(patient.id),
                    "patient_name": patient_name,
                }
            ))
            
            # Debug: log toàn bộ keys và values ngắn của result
            logger.info(f"StreamingService result keys: {list(result.keys())}")
            for k, v in result.items():
                val_preview = str(v)[:200] if v else "(empty)"
                logger.info(f"  result['{k}'] = {val_preview}")
            
            ai_response = result.get("message", "") or result.get("final_response", "")
            
            # StreamingService trả về triage_code ở top-level (extracted từ graph state)
            triage_code = result.get("triage_code") or self._extract_triage_code(ai_response)
            
            # Metadata có thể chứa triage_code nếu top-level không có
            metadata = result.get("metadata", {})
            if not triage_code and metadata:
                triage_code = metadata.get("triage_code") or "CODE_GREEN"
            
            # Parse department: prefer structured code, fallback to text extraction
            department_code = (
                result.get("department_code")
                or metadata.get("department_code", "")
            )
            if department_code:
                recommended_dept = self._find_department_by_code(department_code)
            if not department_code or not recommended_dept:
                recommended_dept = self._extract_department(ai_response)
            
            confidence = self._extract_confidence(ai_response)
            
            # Extract danh sách khoa phù hợp cho Reception xem xét
            matched_departments = (
                result.get("matched_departments")
                or metadata.get("matched_departments")
            )
            # Fallback: parse từ ai_response text (nếu structured data trống)
            if not matched_departments:
                matched_departments = self._extract_matched_departments(ai_response)
            
            logger.info(f"Triage result: code={triage_code}, dept={recommended_dept}, "
                        f"confidence={confidence}, matched_depts={len(matched_departments)}, "
                        f"response_len={len(ai_response)}")
            
            # Cập nhật Visit
            visit.chief_complaint = chief_complaint
            visit.triage_code = triage_code
            visit.triage_ai_response = ai_response
            visit.triage_confidence = confidence
            visit.status = Visit.Status.TRIAGE
            
            if recommended_dept:
                visit.recommended_department = recommended_dept
            
            visit.save()
            
            serializer = self.get_serializer(visit)
            return Response({
                **serializer.data,
                'ai_response': ai_response,
                'triage_code': triage_code,
                'recommended_department_name': recommended_dept.name if recommended_dept else None,
                'triage_confidence': confidence,
                'matched_departments': matched_departments,
            })
            
        except Exception as e:
            logger.error(f"Triage AI error: {e}", exc_info=True)
            return Response(
                {'error': f'Lỗi khi gọi AI: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='confirm-triage')
    def confirm_triage(self, request, pk=None):
        """
        Xác nhận kết quả phân luồng, chốt khoa hướng đến.
        
        POST /reception/visits/{id}/confirm-triage/
        Body: { "department_id": "uuid-of-department" }
        """
        visit = self.get_object()
        department_id = request.data.get('department_id')
        
        if not department_id:
            return Response(
                {'error': 'department_id là bắt buộc'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from apps.core_services.departments.models import Department
        try:
            department = Department.objects.get(id=department_id, is_active=True)
        except Department.DoesNotExist:
            return Response(
                {'error': 'Khoa không tồn tại'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        visit.confirmed_department = department
        visit.triage_confirmed_at = timezone.now()
        visit.status = Visit.Status.WAITING
        visit.save()
        
        serializer = self.get_serializer(visit)
        return Response(serializer.data)

    # --- Helper methods for parsing AI response ---
    
    def _extract_triage_code(self, ai_response: str) -> str:
        """Extract CODE_RED/CODE_YELLOW/CODE_GREEN from AI response."""
        text = ai_response.upper()
        if 'CODE_RED' in text or 'CODE RED' in text:
            return 'CODE_RED'
        elif 'CODE_YELLOW' in text or 'CODE YELLOW' in text:
            return 'CODE_YELLOW'
        return 'CODE_GREEN'
    
    def _find_department_by_code(self, code: str):
        """Look up department by exact code (VD: NOI_TM, CC)."""
        from apps.core_services.departments.models import Department
        try:
            return Department.objects.get(code=code.upper(), is_active=True)
        except Department.DoesNotExist:
            return None
    
    def _extract_department(self, ai_response: str):
        """Try to match department name from AI response against DB."""
        from apps.core_services.departments.models import Department
        departments = Department.objects.filter(is_active=True)
        
        response_lower = ai_response.lower()
        for dept in departments:
            if dept.name.lower() in response_lower or dept.code.lower() in response_lower:
                return dept
        return None
    
    def _extract_confidence(self, ai_response: str) -> int:
        """Extract confidence percentage from AI response."""
        import re
        # Tìm pattern như "85%", "confidence: 90%", "tin cậy: 75%"
        matches = re.findall(r'(\d{1,3})\s*%', ai_response)
        if matches:
            # Lấy số cuối cùng (thường là confidence cuối response)
            for val in reversed(matches):
                num = int(val)
                if 0 <= num <= 100:
                    return num
        return 70  # Default confidence
    
    def _extract_matched_departments(self, ai_response: str) -> list:
        """
        Parse danh sách khoa phù hợp từ AI response text.
        
        Tìm tất cả mã khoa [CODE] trong response và enriches với DB data.
        Đây là fallback khi structured_response không chứa matched_departments.
        """
        import re
        from apps.core_services.departments.models import Department
        
        matched = []
        seen_codes = set()
        triage_codes = {"CODE_BLUE", "CODE_RED", "CODE_YELLOW", "CODE_GREEN"}
        
        # Pattern 1: Format tool output "1. [NOI_TQ] Khoa Nội Tổng Quát\n   Chuyên khoa: ...\n   Độ phù hợp: 0.69"
        entries = re.findall(
            r'\d+\.\s*\[(\w+)\]\s*(.+?)\n\s*Chuyên khoa:\s*(.+?)\n\s*Độ phù hợp:\s*(.+?)(?:\n|$)',
            ai_response
        )
        for code, name, specialties, score in entries:
            code = code.strip()
            if code not in triage_codes and code not in seen_codes:
                seen_codes.add(code)
                matched.append({
                    "code": code,
                    "name": name.strip(),
                    "specialties": specialties.strip(),
                    "score": score.strip(),
                })
        
        # Pattern 2: Fallback - tìm tất cả [DEPT_CODE] và lookup từ DB
        if not matched:
            all_codes = re.findall(r'\[([A-Z_]+)\]', ai_response)
            for code in all_codes:
                if code not in triage_codes and code not in seen_codes:
                    seen_codes.add(code)
                    try:
                        dept = Department.objects.get(code=code, is_active=True)
                        matched.append({
                            "code": dept.code,
                            "name": dept.name,
                            "specialties": dept.specialties[:100] if dept.specialties else "",
                            "score": "text-match",
                        })
                    except Department.DoesNotExist:
                        pass
        
        return matched
