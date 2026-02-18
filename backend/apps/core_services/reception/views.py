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
        vital_signs = request.data.get('vital_signs', {})
        pain_scale = request.data.get('pain_scale')
        consciousness = request.data.get('consciousness', '')
        
        if not chief_complaint:
            return Response(
                {'error': 'chief_complaint là bắt buộc'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Lấy thông tin bệnh nhân
        patient = visit.patient
        patient_name = f"{patient.last_name} {patient.first_name}"
        
        # Query bệnh án cũ (ClinicalRecord) để gửi cho AI
        medical_history_text = ""
        try:
            from apps.medical_services.emr.models import ClinicalRecord
            past_records = ClinicalRecord.objects.filter(
                visit__patient=patient
            ).exclude(visit=visit).order_by('-created_at')[:5]
            
            if past_records.exists():
                history_parts = []
                for rec in past_records:
                    parts = []
                    if rec.chief_complaint:
                        parts.append(f"Lý do khám: {rec.chief_complaint}")
                    if rec.final_diagnosis:
                        parts.append(f"Chẩn đoán: {rec.final_diagnosis}")
                    if rec.treatment_plan:
                        parts.append(f"Điều trị: {rec.treatment_plan}")
                    date_str = rec.created_at.strftime('%d/%m/%Y') if rec.created_at else "N/A"
                    history_parts.append(f"[{date_str}] " + "; ".join(parts))
                medical_history_text = "\n".join(history_parts)
        except Exception as e:
            logger.warning(f"Could not fetch medical history: {e}")
        
        # Format vital signs cho AI
        vital_signs_text = ""
        if vital_signs:
            vs_parts = []
            label_map = {
                'heart_rate': 'Mạch',
                'bp_systolic': 'HA tâm thu',
                'bp_diastolic': 'HA tâm trương',
                'respiratory_rate': 'Nhịp thở',
                'temperature': 'Nhiệt độ',
                'spo2': 'SpO2',
                'weight': 'Cân nặng',
                'height': 'Chiều cao',
            }
            for key, label in label_map.items():
                val = vital_signs.get(key)
                if val is not None:
                    unit_map = {
                        'heart_rate': 'bpm', 'bp_systolic': 'mmHg', 'bp_diastolic': 'mmHg',
                        'respiratory_rate': '/phút', 'temperature': '°C', 'spo2': '%',
                        'weight': 'kg', 'height': 'cm',
                    }
                    vs_parts.append(f"  - {label}: {val} {unit_map.get(key, '')}")
            if vs_parts:
                vital_signs_text = "\n".join(vs_parts)
        
        # Build structured message cho AI triage agent
        structured_message = f"""[TRIAGE_ASSESSMENT_REQUEST]
Mã bệnh nhân: {patient.patient_code}
Họ tên: {patient_name}
Giới tính: {patient.get_gender_display() if hasattr(patient, 'get_gender_display') else patient.gender}
Ngày sinh: {patient.date_of_birth}

LÝ DO KHÁM:
{chief_complaint}
"""
        
        if vital_signs_text:
            structured_message += f"""
CHỈ SỐ SINH HIỆU:
{vital_signs_text}
"""
        
        if pain_scale is not None:
            structured_message += f"  Thang đau: {pain_scale}/10\n"
        if consciousness:
            consciousness_map = {
                'alert': 'Tỉnh táo (Alert)',
                'verbal': 'Đáp ứng lời nói (Verbal)',
                'pain': 'Đáp ứng đau (Pain)',
                'unresponsive': 'Không đáp ứng (Unresponsive)',
            }
            structured_message += f"  Ý thức: {consciousness_map.get(consciousness, consciousness)}\n"
        
        if medical_history_text:
            structured_message += f"""
BỆNH ÁN CŨ:
{medical_history_text}
"""
        
        structured_message += """
YÊU CẦU: 
1. Đánh giá mức độ ưu tiên (triage code: CODE_RED/CODE_YELLOW/CODE_GREEN)
2. Đề xuất khoa phù hợp nhất (chọn 1 trong các khoa có sẵn trong bệnh viện)
3. Ước tính mức độ tin cậy (confidence) từ 0-100%
4. Giải thích ngắn gọn lý do
5. Nếu có chỉ số sinh hiệu bất thường, hãy cảnh báo rõ ràng"""

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
            
            # Extract key factors cho Reception xem nhanh
            key_factors = (
                result.get("key_factors")
                or metadata.get("key_factors")
                or []
            )
            # Fallback: tạo key_factors cơ bản nếu structured data trống
            if not key_factors:
                key_factors = self._extract_key_factors_fallback(
                    ai_response, triage_code
                )
            
            # Cập nhật Visit
            visit.chief_complaint = chief_complaint
            visit.vital_signs = vital_signs if vital_signs else None
            visit.triage_code = triage_code
            visit.triage_ai_response = ai_response
            visit.triage_confidence = confidence
            visit.triage_key_factors = key_factors if key_factors else None
            visit.triage_matched_departments = matched_departments if matched_departments else None
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
                'key_factors': key_factors,
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
        Body: {
            "department_id": "uuid-of-department",        // bắt buộc
            "triage_method": "AI" | "MANUAL",              // bắt buộc
            "triage_code": "CODE_GREEN",                  // optional
            "chief_complaint": "Đau bụng...",             // optional
            "vital_signs": {...},                          // optional
            "triage_confidence": 85,                       // optional
            "triage_ai_response": "...",                   // optional
        }
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
        
        # --- Lưu thông tin phân luồng ---
        # Chief complaint: luôn lưu nếu frontend gửi (kể cả rỗng thay thế cũ)
        if 'chief_complaint' in request.data:
            visit.chief_complaint = request.data['chief_complaint'] or visit.chief_complaint
        
        # Vital signs: luôn lưu nếu frontend gửi (dict non-empty)
        vs = request.data.get('vital_signs')
        if vs and isinstance(vs, dict) and any(v is not None for v in vs.values()):
            visit.vital_signs = vs
        
        # Triage code: từ AI hoặc manual
        if request.data.get('triage_code'):
            visit.triage_code = request.data['triage_code']
        
        # AI confidence + AI response
        confidence = request.data.get('triage_confidence')
        if confidence is not None:
            visit.triage_confidence = confidence
        ai_response = request.data.get('triage_ai_response')
        if ai_response:
            visit.triage_ai_response = ai_response
        
        # --- Triage Method Flag ---
        triage_method = request.data.get('triage_method', '').upper()
        if triage_method in ('AI', 'MANUAL'):
            visit.triage_method = triage_method
        else:
            # Tự suy luận: nếu có AI response → AI, ngược lại → MANUAL
            visit.triage_method = 'AI' if visit.triage_ai_response else 'MANUAL'
        
        # Nếu manual triage (chưa có triage_code), đánh dấu CODE_GREEN mặc định
        if not visit.triage_code:
            visit.triage_code = 'CODE_GREEN'
        
        # Chốt khoa + trạng thái
        visit.confirmed_department = department
        if not visit.recommended_department:
            visit.recommended_department = department
        visit.triage_confirmed_at = timezone.now()
        visit.status = Visit.Status.WAITING
        visit.save()
        
        logger.info(
            f"Triage confirmed: visit={visit.visit_code}, "
            f"dept={department.code}, triage_code={visit.triage_code}, "
            f"method={visit.triage_method}"
        )
        
        serializer = self.get_serializer(visit)
        return Response(serializer.data)

    # --- Helper methods for parsing AI response ---
    
    def _extract_triage_code(self, ai_response: str) -> str:
        """
        Extract CODE_RED/CODE_YELLOW/CODE_GREEN from AI response.
        
        Lấy code CUỐI CÙNG trong text (= kết luận), không phải đầu tiên
        (tránh false positive từ thinking steps nhắc đến CODE_RED).
        """
        text = ai_response.upper()
        codes = ['CODE_BLUE', 'CODE_RED', 'CODE_YELLOW', 'CODE_GREEN']
        
        last_pos = -1
        last_code = 'CODE_GREEN'  # Default
        
        for code in codes:
            pos = text.rfind(code)
            if pos > last_pos:
                last_pos = pos
                last_code = code
        
        return last_code
    
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
    
    def _extract_key_factors_fallback(self, ai_response: str, triage_code: str) -> list:
        """
        Fallback: tạo key_factors cơ bản từ ai_response text khi structured data trống.
        
        Dùng khi triage_node không trả về key_factors (VD: lỗi, legacy flow).
        """
        import re
        factors = []
        
        # Tìm Kết luận phân loại
        conclusion = re.search(
            r'\*\*Kết luận[^*]*\*\*:?\s*(.+?)$',
            ai_response, re.DOTALL | re.IGNORECASE
        )
        if conclusion:
            concl_text = conclusion.group(1).strip().split('\n')[0]
            if len(concl_text) > 80:
                concl_text = concl_text[:80] + '...'
            factors.append(f"Yếu tố chính: {concl_text}")
        
        # Label theo triage code
        code_labels = {
            'CODE_BLUE': 'Hồi sức cấp cứu — xử lý ngay lập tức',
            'CODE_RED': 'Cấp cứu khẩn — dưới 10 phút',
            'CODE_YELLOW': 'Khẩn cấp — dưới 60 phút',
            'CODE_GREEN': 'Không khẩn cấp — có thể chờ',
        }
        if not factors:
            factors.append(f"Phân loại: {code_labels.get(triage_code, triage_code)}")
        
        return factors
