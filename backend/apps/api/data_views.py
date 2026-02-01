"""
Structured Data API Views for Staff Workflows

Provides endpoints for staff to submit structured medical data directly to AI agents.
These endpoints accept structured data (not chat messages) and return AI-processed results.

Use Cases:
- Triage form submission with vital signs and symptoms
- Drug interaction batch checking
- Lab order creation with contraindication checks
- Patient summary generation from EMR data
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List

from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.ai_engine.streaming.service import StreamingService

logger = logging.getLogger(__name__)


# =============================================================================
# TRIAGE ASSESSMENT ENDPOINT
# =============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def submit_triage_assessment(request: HttpRequest) -> JsonResponse:
    """
    Submit structured patient data for AI-assisted triage assessment.
    
    Request Body:
        {
            "patient_id": "BN-001",
            "patient_name": "Nguyen Van A",
            "age": 45,
            "gender": "male",
            "chief_complaint": "Đau ngực trái lan xuống cánh tay",
            "symptoms": ["đau ngực", "khó thở", "vã mồ hôi"],
            "symptom_duration": "2 giờ",
            "vital_signs": {
                "systolic_bp": 160,
                "diastolic_bp": 95,
                "heart_rate": 110,
                "spo2": 94,
                "temperature": 37.2,
                "respiratory_rate": 22
            },
            "medical_history": ["Cao huyết áp", "Tiểu đường type 2"],
            "current_medications": ["Metformin", "Lisinopril"],
            "allergies": ["Penicillin"]
        }
    
    Response:
        {
            "triage_code": "CODE_RED",
            "triage_description": "Cấp cứu khẩn - Đe dọa tính mạng",
            "priority_level": 1,
            "recommended_action": "Chuyển ngay đến Khoa Cấp Cứu",
            "suspected_conditions": ["Nhồi máu cơ tim cấp"],
            "vital_signs_assessment": {...},
            "ai_reasoning": "...",
            "session_id": "triage-xxx"
        }
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
        
        # Validate required fields
        required_fields = ["patient_id", "chief_complaint", "vital_signs"]
        for field in required_fields:
            if field not in body:
                return JsonResponse(
                    {"error": f"Missing required field: {field}", "code": "MISSING_FIELD"},
                    status=400
                )
        
        # Build structured message for triage agent
        patient_id = body.get("patient_id", "")
        patient_name = body.get("patient_name", "Không rõ")
        age = body.get("age", "")
        gender = body.get("gender", "")
        chief_complaint = body.get("chief_complaint", "")
        symptoms = body.get("symptoms", [])
        symptom_duration = body.get("symptom_duration", "")
        vital_signs = body.get("vital_signs", {})
        medical_history = body.get("medical_history", [])
        current_medications = body.get("current_medications", [])
        allergies = body.get("allergies", [])
        
        # Format as structured assessment request
        structured_message = f"""[TRIAGE_ASSESSMENT_REQUEST]
Mã bệnh nhân: {patient_id}
Họ tên: {patient_name}
Tuổi: {age} | Giới tính: {gender}

LÝ DO KHÁM:
{chief_complaint}

TRIỆU CHỨNG:
{', '.join(symptoms) if symptoms else 'Không rõ'}
Thời gian khởi phát: {symptom_duration}

DẤU HIỆU SINH TỒN:
- Huyết áp: {vital_signs.get('systolic_bp', '-')}/{vital_signs.get('diastolic_bp', '-')} mmHg
- Nhịp tim: {vital_signs.get('heart_rate', '-')} bpm
- SpO2: {vital_signs.get('spo2', '-')}%
- Nhiệt độ: {vital_signs.get('temperature', '-')}°C
- Nhịp thở: {vital_signs.get('respiratory_rate', '-')} lần/phút

TIỀN SỬ BỆNH:
{', '.join(medical_history) if medical_history else 'Không có'}

THUỐC ĐANG DÙNG:
{', '.join(current_medications) if current_medications else 'Không có'}

DỊ ỨNG:
{', '.join(allergies) if allergies else 'Không có'}

YÊU CẦU: Đánh giá mức độ ưu tiên (triage code), phân luồng khoa phù hợp, và cảnh báo nếu cần can thiệp khẩn cấp."""
        
        # Create patient context for agent
        patient_context = {
            "patient_id": patient_id,
            "patient_name": patient_name,
            "vitals": vital_signs,
            "medical_history": [{"condition": h} for h in medical_history],
            "current_medications": current_medications,
            "allergies": allergies,
        }
        
        # Generate session ID
        import time
        session_id = f"triage-{patient_id}-{int(time.time())}"
        
        # Get AI response synchronously
        streaming_service = StreamingService()
        result = asyncio.run(streaming_service.get_full_response(
            message=structured_message,
            session_id=session_id,
            patient_context=patient_context
        ))
        
        # Parse and structure the response
        response = {
            "session_id": session_id,
            "patient_id": patient_id,
            "ai_response": result.get("response", ""),
            "agent": result.get("agent", "triage"),
            "metadata": result.get("metadata", {}),
            "input_summary": {
                "chief_complaint": chief_complaint,
                "vital_signs": vital_signs,
            }
        }
        
        return JsonResponse(response, json_dumps_params={'ensure_ascii': False})
        
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON", "code": "INVALID_JSON"},
            status=400
        )
    except Exception as e:
        logger.error(f"Triage assessment error: {e}", exc_info=True)
        return JsonResponse(
            {"error": str(e), "code": "INTERNAL_ERROR"},
            status=500
        )


# =============================================================================
# DRUG INTERACTION CHECK ENDPOINT
# =============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def check_drug_interactions(request: HttpRequest) -> JsonResponse:
    """
    Check for drug interactions from a structured medication list.
    
    Request Body:
        {
            "patient_id": "BN-001",
            "medications": [
                {"name": "Aspirin", "dose": "100mg", "frequency": "1 lần/ngày"},
                {"name": "Warfarin", "dose": "5mg", "frequency": "1 lần/ngày"},
                {"name": "Metformin", "dose": "500mg", "frequency": "2 lần/ngày"}
            ],
            "allergies": ["Penicillin"],
            "conditions": ["Tiểu đường type 2", "Rung nhĩ"]
        }
    
    Response:
        {
            "interactions_found": true,
            "interactions": [
                {
                    "drugs": ["Aspirin", "Warfarin"],
                    "severity": "MAJOR",
                    "description": "Tăng nguy cơ chảy máu",
                    "recommendation": "KHÔNG dùng chung"
                }
            ],
            "safe_combinations": [...],
            "ai_analysis": "...",
            "session_id": "drug-xxx"
        }
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
        
        medications = body.get("medications", [])
        if not medications:
            return JsonResponse(
                {"error": "Medications list is required", "code": "MISSING_MEDICATIONS"},
                status=400
            )
        
        patient_id = body.get("patient_id", "unknown")
        allergies = body.get("allergies", [])
        conditions = body.get("conditions", [])
        
        # Format medication list
        med_list = []
        for med in medications:
            if isinstance(med, dict):
                name = med.get("name", str(med))
                dose = med.get("dose", "")
                freq = med.get("frequency", "")
                med_list.append(f"{name} {dose} {freq}".strip())
            else:
                med_list.append(str(med))
        
        # Build structured message for pharmacist agent
        structured_message = f"""[DRUG_INTERACTION_CHECK]
Mã bệnh nhân: {patient_id}

DANH SÁCH THUỐC CẦN KIỂM TRA:
{chr(10).join(f'- {m}' for m in med_list)}

TIỀN SỬ DỊ ỨNG:
{', '.join(allergies) if allergies else 'Không có'}

BỆNH NỀN:
{', '.join(conditions) if conditions else 'Không rõ'}

YÊU CẦU: 
1. Kiểm tra tương tác thuốc-thuốc
2. Kiểm tra chống chỉ định với bệnh nền
3. Kiểm tra dị ứng chéo
4. Đề xuất thay thế nếu cần"""
        
        import time
        session_id = f"drug-{patient_id}-{int(time.time())}"
        
        streaming_service = StreamingService()
        result = asyncio.run(streaming_service.get_full_response(
            message=structured_message,
            session_id=session_id,
            patient_context={"patient_id": patient_id, "allergies": allergies}
        ))
        
        response = {
            "session_id": session_id,
            "patient_id": patient_id,
            "medications_checked": med_list,
            "ai_analysis": result.get("response", ""),
            "agent": result.get("agent", "pharmacist"),
            "metadata": result.get("metadata", {}),
        }
        
        return JsonResponse(response, json_dumps_params={'ensure_ascii': False})
        
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON", "code": "INVALID_JSON"},
            status=400
        )
    except Exception as e:
        logger.error(f"Drug interaction check error: {e}", exc_info=True)
        return JsonResponse(
            {"error": str(e), "code": "INTERNAL_ERROR"},
            status=500
        )


# =============================================================================
# LAB ORDER CREATION ENDPOINT
# =============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def create_lab_order(request: HttpRequest) -> JsonResponse:
    """
    Create a lab order with AI-assisted contraindication checking.
    
    Request Body:
        {
            "patient_id": "BN-001",
            "ordering_physician": "BS. Nguyen Van B",
            "order_type": "Lab Test",
            "tests": ["CBC", "BMP", "Liver Function", "HbA1c"],
            "clinical_indication": "Theo dõi tiểu đường",
            "urgency": "routine",
            "special_instructions": "Nhịn ăn 8 giờ"
        }
    
    Response:
        {
            "order_id": "ORD-xxx",
            "status": "PENDING",
            "tests_ordered": [...],
            "contraindication_check": "PASSED",
            "preparation_instructions": "...",
            "estimated_completion": "2-4 giờ",
            "ai_notes": "..."
        }
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
        
        patient_id = body.get("patient_id")
        if not patient_id:
            return JsonResponse(
                {"error": "Patient ID is required", "code": "MISSING_PATIENT_ID"},
                status=400
            )
        
        tests = body.get("tests", [])
        if not tests:
            return JsonResponse(
                {"error": "Tests list is required", "code": "MISSING_TESTS"},
                status=400
            )
        
        order_type = body.get("order_type", "Lab Test")
        ordering_physician = body.get("ordering_physician", "")
        clinical_indication = body.get("clinical_indication", "")
        urgency = body.get("urgency", "routine")
        special_instructions = body.get("special_instructions", "")
        
        # Build structured message for paraclinical agent
        structured_message = f"""[LAB_ORDER_REQUEST]
Mã bệnh nhân: {patient_id}
Bác sĩ chỉ định: {ordering_physician}

LOẠI Y LỆNH: {order_type}
MỨC ĐỘ KHẨN: {urgency}

DANH SÁCH XÉT NGHIỆM:
{chr(10).join(f'- {t}' for t in tests)}

CHỈ ĐỊNH LÂM SÀNG:
{clinical_indication}

HƯỚNG DẪN ĐẶC BIỆT:
{special_instructions if special_instructions else 'Không có'}

YÊU CẦU:
1. Tiếp nhận và xác thực y lệnh
2. Kiểm tra chống chỉ định (nếu có)
3. Tạo mã y lệnh và hướng dẫn chuẩn bị cho bệnh nhân"""
        
        import time
        session_id = f"lab-{patient_id}-{int(time.time())}"
        
        streaming_service = StreamingService()
        result = asyncio.run(streaming_service.get_full_response(
            message=structured_message,
            session_id=session_id,
            patient_context={"patient_id": patient_id}
        ))
        
        # Generate order ID
        from datetime import datetime
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        response = {
            "order_id": order_id,
            "session_id": session_id,
            "patient_id": patient_id,
            "status": "PENDING",
            "tests_ordered": tests,
            "urgency": urgency,
            "ai_response": result.get("response", ""),
            "agent": result.get("agent", "paraclinical"),
            "metadata": result.get("metadata", {}),
        }
        
        return JsonResponse(response, json_dumps_params={'ensure_ascii': False})
        
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON", "code": "INVALID_JSON"},
            status=400
        )
    except Exception as e:
        logger.error(f"Lab order creation error: {e}", exc_info=True)
        return JsonResponse(
            {"error": str(e), "code": "INTERNAL_ERROR"},
            status=500
        )


# =============================================================================
# PATIENT SUMMARY GENERATION ENDPOINT
# =============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def generate_patient_summary(request: HttpRequest) -> JsonResponse:
    """
    Generate an AI summary from structured patient EMR data.
    
    Request Body:
        {
            "patient_id": "BN-001",
            "patient_name": "Nguyen Van A",
            "age": 65,
            "gender": "male",
            "admission_date": "2026-01-25",
            "chief_complaint": "Đau ngực",
            "diagnosis": ["I21.0 - Nhồi máu cơ tim ST chênh lên"],
            "procedures": ["PCI LAD với DES"],
            "lab_results": [
                {"test": "Troponin I", "value": 2.5, "unit": "ng/mL", "flag": "HIGH"},
                {"test": "BNP", "value": 450, "unit": "pg/mL", "flag": "HIGH"}
            ],
            "imaging_results": [
                {"exam": "Echo tim", "finding": "EF 45%, giảm vận động thành trước"}
            ],
            "current_medications": ["Aspirin", "Clopidogrel", "Atorvastatin"],
            "summary_type": "discharge"
        }
    
    Response:
        {
            "summary": "...",
            "key_findings": [...],
            "recommendations": [...],
            "follow_up_instructions": "...",
            "session_id": "summary-xxx"
        }
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
        
        patient_id = body.get("patient_id")
        if not patient_id:
            return JsonResponse(
                {"error": "Patient ID is required", "code": "MISSING_PATIENT_ID"},
                status=400
            )
        
        patient_name = body.get("patient_name", "")
        age = body.get("age", "")
        gender = body.get("gender", "")
        admission_date = body.get("admission_date", "")
        chief_complaint = body.get("chief_complaint", "")
        diagnosis = body.get("diagnosis", [])
        procedures = body.get("procedures", [])
        lab_results = body.get("lab_results", [])
        imaging_results = body.get("imaging_results", [])
        current_medications = body.get("current_medications", [])
        summary_type = body.get("summary_type", "general")
        
        # Format lab results
        lab_str = ""
        for lab in lab_results:
            if isinstance(lab, dict):
                flag = f" [{lab.get('flag', '')}]" if lab.get('flag') else ""
                lab_str += f"- {lab.get('test', '')}: {lab.get('value', '')} {lab.get('unit', '')}{flag}\n"
            else:
                lab_str += f"- {lab}\n"
        
        # Format imaging results
        imaging_str = ""
        for img in imaging_results:
            if isinstance(img, dict):
                imaging_str += f"- {img.get('exam', '')}: {img.get('finding', '')}\n"
            else:
                imaging_str += f"- {img}\n"
        
        # Build structured message for summarize agent
        structured_message = f"""[PATIENT_SUMMARY_REQUEST]
Loại tóm tắt: {summary_type.upper()}

THÔNG TIN BỆNH NHÂN:
Mã BN: {patient_id}
Họ tên: {patient_name}
Tuổi: {age} | Giới: {gender}
Ngày nhập viện: {admission_date}

LÝ DO NHẬP VIỆN:
{chief_complaint}

CHẨN ĐOÁN:
{chr(10).join(f'- {d}' for d in diagnosis) if diagnosis else 'Chưa có'}

THỦ THUẬT/PHẪU THUẬT:
{chr(10).join(f'- {p}' for p in procedures) if procedures else 'Không có'}

KẾT QUẢ XÉT NGHIỆM:
{lab_str if lab_str else 'Không có dữ liệu'}

KẾT QUẢ HÌNH ẢNH:
{imaging_str if imaging_str else 'Không có dữ liệu'}

THUỐC ĐANG DÙNG:
{chr(10).join(f'- {m}' for m in current_medications) if current_medications else 'Không có'}

YÊU CẦU: Tạo bản tóm tắt {summary_type} cho bệnh nhân với các phát hiện chính, khuyến nghị điều trị, và hướng dẫn theo dõi."""
        
        import time
        session_id = f"summary-{patient_id}-{int(time.time())}"
        
        patient_context = {
            "patient_id": patient_id,
            "patient_name": patient_name,
            "current_medications": current_medications,
            "lab_results": lab_results,
        }
        
        streaming_service = StreamingService()
        result = asyncio.run(streaming_service.get_full_response(
            message=structured_message,
            session_id=session_id,
            patient_context=patient_context
        ))
        
        response = {
            "session_id": session_id,
            "patient_id": patient_id,
            "summary_type": summary_type,
            "summary": result.get("response", ""),
            "agent": result.get("agent", "summarize"),
            "metadata": result.get("metadata", {}),
        }
        
        return JsonResponse(response, json_dumps_params={'ensure_ascii': False})
        
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON", "code": "INVALID_JSON"},
            status=400
        )
    except Exception as e:
        logger.error(f"Patient summary generation error: {e}", exc_info=True)
        return JsonResponse(
            {"error": str(e), "code": "INTERNAL_ERROR"},
            status=500
        )


# =============================================================================
# VITAL SIGNS ASSESSMENT ENDPOINT (Quick, no LLM)
# =============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def assess_vitals(request: HttpRequest) -> JsonResponse:
    """
    Quick vital signs assessment without LLM (rule-based).
    For immediate triage decisions.
    
    Request Body:
        {
            "systolic_bp": 180,
            "diastolic_bp": 110,
            "heart_rate": 120,
            "spo2": 92,
            "temperature": 39.5,
            "respiratory_rate": 28
        }
    
    Response:
        {
            "triage_code": "CODE_RED",
            "alerts": ["Huyết áp tâm thu cao nguy hiểm", ...],
            "recommendation": "Chuyển Khoa Cấp Cứu ngay"
        }
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
        
        systolic_bp = body.get("systolic_bp")
        diastolic_bp = body.get("diastolic_bp")
        heart_rate = body.get("heart_rate")
        spo2 = body.get("spo2")
        temperature = body.get("temperature")
        respiratory_rate = body.get("respiratory_rate")
        
        alerts = []
        triage_code = "CODE_GREEN"
        
        # Blood pressure assessment
        if systolic_bp:
            if systolic_bp > 180 or systolic_bp < 90:
                alerts.append(f"Huyết áp tâm thu: {systolic_bp} mmHg - NGUY HIỂM")
                triage_code = "CODE_RED"
            elif systolic_bp > 140:
                alerts.append(f"Huyết áp tâm thu: {systolic_bp} mmHg - Cao")
                if triage_code == "CODE_GREEN":
                    triage_code = "CODE_YELLOW"
        
        # Heart rate assessment
        if heart_rate:
            if heart_rate > 150 or heart_rate < 40:
                alerts.append(f"Nhịp tim: {heart_rate} bpm - NGUY HIỂM")
                triage_code = "CODE_RED"
            elif heart_rate > 100 or heart_rate < 60:
                alerts.append(f"Nhịp tim: {heart_rate} bpm - Bất thường")
                if triage_code == "CODE_GREEN":
                    triage_code = "CODE_YELLOW"
        
        # SpO2 assessment
        if spo2:
            if spo2 < 90:
                alerts.append(f"SpO2: {spo2}% - THIẾU OXY NGHIÊM TRỌNG")
                triage_code = "CODE_RED"
            elif spo2 < 95:
                alerts.append(f"SpO2: {spo2}% - Thấp")
                if triage_code == "CODE_GREEN":
                    triage_code = "CODE_YELLOW"
        
        # Temperature assessment
        if temperature:
            if temperature > 40.5 or temperature < 35:
                alerts.append(f"Nhiệt độ: {temperature}°C - NGUY HIỂM")
                triage_code = "CODE_RED"
            elif temperature > 38:
                alerts.append(f"Nhiệt độ: {temperature}°C - Sốt")
        
        # Respiratory rate assessment
        if respiratory_rate:
            if respiratory_rate > 30 or respiratory_rate < 10:
                alerts.append(f"Nhịp thở: {respiratory_rate}/phút - NGUY HIỂM")
                triage_code = "CODE_RED"
        
        # Generate recommendation
        recommendations = {
            "CODE_RED": "Chuyển Khoa Cấp Cứu NGAY LẬP TỨC",
            "CODE_YELLOW": "Ưu tiên khám trong vòng 60 phút",
            "CODE_GREEN": "Khám theo thứ tự bình thường",
        }
        
        response = {
            "triage_code": triage_code,
            "alerts": alerts if alerts else ["Các chỉ số sinh tồn trong giới hạn bình thường"],
            "recommendation": recommendations.get(triage_code, ""),
            "input": {
                "systolic_bp": systolic_bp,
                "diastolic_bp": diastolic_bp,
                "heart_rate": heart_rate,
                "spo2": spo2,
                "temperature": temperature,
                "respiratory_rate": respiratory_rate,
            }
        }
        
        return JsonResponse(response, json_dumps_params={'ensure_ascii': False})
        
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON", "code": "INVALID_JSON"},
            status=400
        )
    except Exception as e:
        logger.error(f"Vital signs assessment error: {e}", exc_info=True)
        return JsonResponse(
            {"error": str(e), "code": "INTERNAL_ERROR"},
            status=500
        )


# =============================================================================
# AI SUGGESTIONS RETRIEVAL ENDPOINT
# =============================================================================

@csrf_exempt
@require_http_methods(["GET"])
def get_ai_suggestions(request: HttpRequest, visit_id: str) -> JsonResponse:
    """
    Retrieve saved AI suggestions for a specific visit's clinical record.
    
    Path Parameter:
        visit_id (UUID): The ID of the visit.
    
    Response:
        {
            "visit_id": "uuid",
            "visit_code": "VISIT-xxx",
            "ai_suggestions": {...},  // The raw AI suggestion JSON
            "is_finalized": false
        }
    """
    try:
        from apps.medical_services.emr.models import ClinicalRecord
        
        record = ClinicalRecord.objects.select_related('visit').get(visit__id=visit_id)
        
        response = {
            "visit_id": str(record.visit.id),
            "visit_code": record.visit.visit_code,
            "ai_suggestions": record.ai_suggestion_json,
            "is_finalized": record.is_finalized,
        }
        
        return JsonResponse(response, json_dumps_params={'ensure_ascii': False})
        
    except ClinicalRecord.DoesNotExist:
        return JsonResponse(
            {"error": "Clinical record not found for this visit", "code": "NOT_FOUND"},
            status=404
        )
    except Exception as e:
        logger.error(f"Get AI suggestions error: {e}", exc_info=True)
        return JsonResponse(
            {"error": str(e), "code": "INTERNAL_ERROR"},
            status=500
        )
