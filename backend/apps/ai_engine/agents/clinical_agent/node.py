# apps/ai_engine/agents/clinical_agent/node.py
"""
Clinical Agent Node - Bác sĩ chẩn đoán

REFACTORED cho Real Token Streaming:
- Phase 1: LLM stream text thinking (hiển thị realtime)
- Phase 2: Parse text thành structured response
"""

from typing import Dict, Any, List
import re
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage

from apps.ai_engine.graph.state import AgentState
from apps.ai_engine.graph.llm_config import llm_pro, logging_node_execution
from apps.ai_engine.agents.message_utils import convert_and_filter_messages, log_llm_response, extract_final_response
from apps.ai_engine.graph.prompts import get_system_prompt


def extract_thinking_steps(text: str) -> List[str]:
    """Extract thinking steps từ text với format **Bước X:**"""
    steps = []
    pattern = r'\*\*Bước\s*\d+[^*]*\*\*:?\s*([^\*]+?)(?=\*\*Bước|\*\*Kết luận|$)'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    for i, match in enumerate(matches, 1):
        step_text = match.strip()
        if step_text:
            if len(step_text) > 200:
                step_text = step_text[:200] + "..."
            steps.append(f"Bước {i}: {step_text}")
    
    return steps if steps else ["Đã phân tích triệu chứng và đưa ra chẩn đoán"]


def extract_urgency(text: str) -> bool:
    """Check if urgent care is required."""
    urgent_keywords = ["URGENT_HIGH", "cấp cứu ngay", "đe dọa tính mạng", "nguy hiểm"]
    return any(kw.lower() in text.lower() for kw in urgent_keywords)


def extract_diagnosis(text: str) -> List[str]:
    """Extract differential diagnosis từ text."""
    diagnoses = []
    pattern = r'(?:^|\n)\s*\d+\.\s*(.+?)(?:\s*-|\s*\(|$)'
    matches = re.findall(pattern, text, re.MULTILINE)
    for match in matches[:5]:  # Max 5
        match = match.strip()
        if len(match) > 5 and len(match) < 100:
            diagnoses.append(match)
    return diagnoses if diagnoses else []


def extract_icd_codes(text: str) -> List[Dict[str, Any]]:
    """
    Extract ICD-10 codes từ text response.
    
    Format expected:
    - [ICD_CODE] I21.9 | Nhồi máu cơ tim cấp | loai:main | confidence:0.85
    
    Fallback: tìm pattern ICD-10 code dạng chữ+số (A00-Z99)
    """
    codes = []
    
    # Primary pattern: [ICD_CODE] format từ prompt
    icd_pattern = r'\[ICD_CODE\]\s*([A-Z]\d{2}(?:\.\d{1,2})?)\s*\|\s*([^|]+?)\s*\|\s*loai:\s*(main|sub)\s*\|\s*confidence:\s*([\d.]+)'
    matches = re.findall(icd_pattern, text, re.IGNORECASE)
    
    for match in matches:
        code, name, icd_type, confidence = match
        try:
            conf = float(confidence)
        except ValueError:
            conf = 0.5
        codes.append({
            "code": code.upper().strip(),
            "name": name.strip(),
            "type": icd_type.lower().strip(),
            "confidence": min(max(conf, 0.0), 1.0),
        })
    
    # Fallback: regex tìm pattern ICD-10 trong text nếu không có [ICD_CODE]
    if not codes:
        fallback_pattern = r'([A-Z]\d{2}(?:\.\d{1,2})?)\s*[\(\-–:]\s*([^)\n,]{5,60})'
        fallback_matches = re.findall(fallback_pattern, text)
        for code, name in fallback_matches[:8]:
            # Kiểm tra code hợp lệ (A00-Z99)
            letter = code[0]
            if letter.isalpha() and 'A' <= letter <= 'Z':
                codes.append({
                    "code": code.upper().strip(),
                    "name": name.strip().rstrip(')'),
                    "type": "main" if len(codes) == 0 else "sub",
                    "confidence": 0.6,
                })
    
    return codes


def validate_icd_codes_against_db(codes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate extracted ICD codes against the hospital's ICD10Code database.
    Adds 'in_system' flag and 'system_name' for each code.
    
    Returns:
        Updated list with in_system=True/False per code
    """
    if not codes:
        return codes
    
    try:
        from apps.core_services.core.models import ICD10Code
        
        # Lấy tất cả codes cần check
        code_values = [c["code"] for c in codes]
        
        # Query DB một lần (hiệu quả hơn N queries)
        db_codes = ICD10Code.objects.filter(
            code__in=code_values
        ).values_list("code", "name")
        
        # Build lookup map
        db_map = {row[0]: row[1] for row in db_codes}
        
        # Annotate mỗi code
        for c in codes:
            if c["code"] in db_map:
                c["in_system"] = True
                c["system_name"] = db_map[c["code"]]
            else:
                c["in_system"] = False
                c["system_name"] = None
        
        in_count = sum(1 for c in codes if c["in_system"])
        ext_count = len(codes) - in_count
        print(f"[CLINICAL] ICD validation: {in_count} in DB, {ext_count} external")
        
    except Exception as e:
        print(f"[CLINICAL] ICD DB validation error (non-fatal): {e}")
        # Nếu lỗi DB, đánh tất cả là unknown
        for c in codes:
            c["in_system"] = None
            c["system_name"] = None
    
    return codes


def extract_medical_keywords(patient_text: str) -> List[str]:
    """
    Phase 1: Dùng llm_flash (nhẹ, nhanh) để trích xuất keywords y khoa
    từ thông tin bệnh nhân (sinh hiệu, lý do khám, bệnh sử, khám lâm sàng).
    
    Returns:
        List các keywords y khoa (ví dụ: ['đau bụng', 'tăng huyết áp', 'đái tháo đường'])
    """
    from apps.ai_engine.graph.llm_config import llm_flash
    
    prompt_text = f"""Bạn là trợ lý y tế. Từ thông tin bệnh nhân dưới đây, hãy trích xuất TẤT CẢ các từ khóa y khoa quan trọng.

Bao gồm:
- Triệu chứng (đau bụng, khó thở, sốt, ...)
- Bệnh nền/tiền sử (tăng huyết áp, đái tháo đường, gút, ...)
- Dấu hiệu sinh tồn bất thường
- Cơ quan/hệ cơ quan liên quan (tim, dạ dày, phổi, ...)

CHỈ trả về danh sách từ khóa, PHÂN CÁCH bằng dấu phẩy. KHÔNG giải thích.

Ví dụ output: đau bụng, tăng huyết áp, đái tháo đường type 2, nhịp tim nhanh, viêm dạ dày

THÔNG TIN BỆNH NHÂN:
{patient_text[:1500]}"""
    
    try:
        response = llm_flash.invoke([HumanMessage(content=prompt_text)])
        raw_content = response.content
        
        # Gemini có thể trả content dạng list (parts) hoặc string
        if isinstance(raw_content, list):
            raw_keywords = " ".join(
                part.get("text", str(part)) if isinstance(part, dict) else str(part)
                for part in raw_content
            ).strip()
        else:
            raw_keywords = str(raw_content).strip()
        
        # Parse comma-separated keywords
        keywords = [k.strip() for k in raw_keywords.split(',') if k.strip()]
        
        print(f"[CLINICAL][ICD-KW] Extracted {len(keywords)} medical keywords: {keywords[:10]}")
        return keywords
    
    except Exception as e:
        print(f"[CLINICAL][ICD-KW] Error extracting keywords: {e}")
        return []


def search_icd_by_medical_keywords(keywords: List[str]) -> str:
    """
    Phase 2: Dùng medical keywords (đã được LLM trích xuất) để tìm ICD codes
    trong DB bệnh viện. Trả về top ~15 codes phù hợp nhất.
    """
    if not keywords:
        return ""
    
    try:
        from apps.core_services.core.models import ICD10Code
        from django.db.models import Q
        
        # Symptom→ICD category mapping cho tìm kiếm chính xác hơn
        symptom_category_map = {
            'đau bụng': ['R10', 'K21', 'K25', 'K29', 'K80', 'K85'],
            'đau ngực': ['I20', 'I21', 'R'],
            'đau đầu': ['R51', 'G43', 'I63', 'I64'],
            'đau lưng': ['M51', 'M54', 'M54.5'],
            'sốt': ['R50', 'A09', 'J'],
            'ho': ['J00', 'J06', 'J18', 'J44', 'J45'],
            'khó thở': ['J44', 'J45', 'J18', 'I'],
            'tăng huyết áp': ['I10', 'I11'],
            'huyết áp': ['I10', 'I11'],
            'tiểu đường': ['E10', 'E11', 'E11.9'],
            'đái tháo đường': ['E10', 'E11', 'E11.9'],
            'nhồi máu': ['I21', 'I63'],
            'đột quỵ': ['I63', 'I64'],
            'viêm phổi': ['J12', 'J15', 'J18'],
            'viêm dạ dày': ['K29', 'K21', 'K25'],
            'loét dạ dày': ['K25'],
            'trào ngược': ['K21'],
            'xơ gan': ['K74'],
            'viêm gan': ['B18', 'B18.1'],
            'sỏi mật': ['K80'],
            'viêm tụy': ['K85'],
            'suy thận': ['N18'],
            'nhiễm trùng tiểu': ['N39.0', 'N30'],
            'gút': ['M15', 'M17'],
            'thoái hóa khớp': ['M17'],
            'thoát vị đĩa đệm': ['M51'],
            'hen': ['J45'],
            'copd': ['J44'],
            'trầm cảm': ['F32', 'F33'],
            'lo âu': ['F41', 'F41.0'],
            'động kinh': ['G40'],
            'nhịp tim nhanh': ['I20', 'I21', 'I'],
            'béo phì': ['E66'],
            'cholesterol': ['E78.0', 'E78.5'],
            'rối loạn lipid': ['E78.0', 'E78.5'],
            'ung thư': ['C'],
            'tiêu chảy': ['A09'],
            'cảm lạnh': ['J00'],
            'viêm amidan': ['J03'],
            'migraine': ['G43'],
        }
        
        # Build Q filter từ medical keywords
        q_filter = Q()
        search_codes = set()
        
        for keyword in keywords:
            kw_lower = keyword.lower().strip()
            
            # Direct name search
            q_filter |= Q(name__icontains=kw_lower)
            
            # Check symptom→category map
            for symptom, codes in symptom_category_map.items():
                if symptom in kw_lower or kw_lower in symptom:
                    search_codes.update(codes)
            
            # From individual words in multi-word keywords  
            for word in kw_lower.split():
                if len(word) >= 3:
                    q_filter |= Q(name__icontains=word)
                    for symptom, codes in symptom_category_map.items():
                        if word in symptom or symptom in word:
                            search_codes.update(codes)
        
        # Query 1: Direct name match
        name_results = list(ICD10Code.objects.filter(q_filter).values_list("code", "name")[:12])
        
        # Query 2: Category code match
        map_results = []
        if search_codes:
            code_q = Q()
            for sc in search_codes:
                code_q |= Q(code__startswith=sc)
            map_results = list(ICD10Code.objects.filter(code_q).values_list("code", "name")[:10])
        
        # Merge + deduplicate
        seen = set()
        all_results = []
        for code, name in name_results + map_results:
            if code not in seen:
                seen.add(code)
                all_results.append((code, name))
        
        if not all_results:
            print(f"[CLINICAL][ICD-RAG] No ICD matches for keywords: {keywords[:5]}")
            return ""
        
        all_results = all_results[:15]
        
        print(f"[CLINICAL][ICD-RAG] Found {len(all_results)} relevant ICD codes from DB")
        for code, name in all_results[:5]:
            print(f"[CLINICAL][ICD-RAG]   → {code}: {name}")
        
        lines = ["## MÃ ICD-10 LIÊN QUAN TỪ DANH MỤC BỆNH VIỆN"]
        lines.append("")
        lines.append("Các mã ICD-10 dưới đây được TÌM KIẾM từ danh mục bệnh viện dựa trên triệu chứng và bệnh nền.")
        lines.append("Bạn PHẢI ưu TIÊN chọn mã từ danh sách này.")
        lines.append("Nếu không tìm thấy mã phù hợp, có thể đề xuất mã ICD-10 chuẩn quốc tế nhưng PHẢI ghi rõ đó là mã ngoài hệ thống.")
        lines.append("")
        for code, name in all_results:
            lines.append(f"- {code}: {name}")
        lines.append("")
        
        return "\n".join(lines)
    
    except Exception as e:
        print(f"[CLINICAL][ICD-RAG] DB search error: {e}")
        return ""


def _extract_patient_context(user_message: str) -> str:
    """
    Trích xuất phần thông tin bệnh nhân từ message 
    (bỏ qua prefix hệ thống như [CLINICAL_ANALYSIS] Tôi là bác sĩ...).
    Giữ lại: sinh hiệu, lý do khám, tóm tắt bệnh án, bệnh sử, khám lâm sàng.
    """
    # Tìm các section markers
    sections = []
    markers = ['CHỈ SỐ SINH HIỆU', 'LÝ DO KHÁM', 'TÓM TẮT BỆNH ÁN', 
               'BỆNH SỬ', 'KHÁM LÂM SÀNG', 'CƠ SỞ PHÂN LUỒNG', 'LƯU Ý TỪ AI']
    
    for marker in markers:
        idx = user_message.find(marker)
        if idx >= 0:
            # Get content from marker to next marker or end
            start = idx
            end = len(user_message)
            for other_marker in markers:
                other_idx = user_message.find(other_marker, start + len(marker))
                if other_idx > start and other_idx < end:
                    end = other_idx
            sections.append(user_message[start:end].strip())
    
    if sections:
        return "\n".join(sections)
    
    # Fallback: return last 800 chars (likely contains patient info)
    return user_message[-800:] if len(user_message) > 800 else user_message


def clinical_node(state: AgentState) -> Dict[str, Any]:
    """
    Clinical Agent (Bác sĩ chẩn đoán) - Real Token Streaming
    
    Flow:
    Phase 1: llm_flash trích xuất medical keywords từ patient context
    Phase 2: Keywords → search ICD-10 DB bệnh viện (RAG)
    Phase 3: Inject matched ICD codes vào prompt → llm_pro phân tích
    Phase 4: Parse text thành structured response + validate ICD
    """
    logging_node_execution("CLINICAL")
    messages = state["messages"]
    
    # Convert và filter messages
    converted_messages, last_user_message = convert_and_filter_messages(messages, "CLINICAL")
    
    prompt = [SystemMessage(content=get_system_prompt("clinical"))] + converted_messages
    
    try:
        # ── PHASE 1: EXTRACT MEDICAL KEYWORDS ─────────────────
        patient_context = _extract_patient_context(last_user_message or "")
        print(f"[CLINICAL][ICD-P1] Patient context length: {len(patient_context)} chars")
        
        medical_keywords = extract_medical_keywords(patient_context)
        
        # ── PHASE 2: RAG SEARCH ICD DB ────────────────────────
        icd_context = ""
        if medical_keywords:
            icd_context = search_icd_by_medical_keywords(medical_keywords)
        
        if icd_context:
            prompt.insert(1, SystemMessage(content=icd_context))
            print("[CLINICAL][ICD-P2] ✅ ICD context INJECTED into prompt")
        else:
            print("[CLINICAL][ICD-P2] ⚠ No relevant ICD codes found in DB")
        
        print(f"[CLINICAL][ICD] Total prompt messages: {len(prompt)}")
        # ── END ICD RAG ───────────────────────────────────────
        
        # Direct LLM invoke (text response, không structured output)
        response = llm_pro.invoke(prompt)
        
        # Log response
        text_analysis = log_llm_response(response, "CLINICAL")
        
        # Extract components từ text
        thinking_steps = extract_thinking_steps(text_analysis)
        requires_urgent = extract_urgency(text_analysis)
        diagnoses = extract_diagnosis(text_analysis)
        icd_codes = extract_icd_codes(text_analysis)
        
        # Validate ICD codes against hospital database
        if icd_codes:
            icd_codes = validate_icd_codes_against_db(icd_codes)
        
        print(f"[CLINICAL] Thinking steps: {len(thinking_steps)}")
        print(f"[CLINICAL] Urgent care: {requires_urgent}")
        print(f"[CLINICAL] Diagnoses found: {len(diagnoses)}")
        print(f"[CLINICAL] ICD codes found: {len(icd_codes)}")
        
        # Check if any ICD code is not in system
        has_external_codes = any(
            c.get("in_system") is False for c in icd_codes
        ) if icd_codes else False
        
        icd_source_warning = None
        if has_external_codes:
            external_codes = [c["code"] for c in icd_codes if not c.get("in_system")]
            icd_source_warning = (
                f"⚠ Một số mã ICD ({', '.join(external_codes)}) "
                f"không có trong danh mục ICD-10 của bệnh viện. "
                f"AI đã sử dụng kiến thức bên ngoài để đề xuất — "
                f"bác sĩ cần kiểm tra và chọn mã phù hợp trong hệ thống."
            )
        
        # Build structured response
        structured_data = {
            "thinking_progress": thinking_steps,
            "final_response": extract_final_response(text_analysis, "Kết luận"),
            "confidence_score": 0.8 if diagnoses else 0.6,
            "differential_diagnosis": diagnoses,
            "requires_urgent_care": requires_urgent,
            "icd_codes": icd_codes if icd_codes else None,
            "icd_source_warning": icd_source_warning,
        }
        
        # Tạo message với structured data
        message = AIMessage(
            content=text_analysis,
            additional_kwargs={
                "agent": "clinical",
                "structured_response": structured_data,
                "thinking_progress": thinking_steps,
                "confidence_score": structured_data["confidence_score"]
            }
        )
        
    except Exception as e:
        print(f"[CLINICAL] Error: {e}")
        message = AIMessage(
            content=f"[Lỗi xử lý] Xin vui lòng mô tả lại triệu chứng của bạn.",
            additional_kwargs={"agent": "clinical", "error": str(e)}
        )
    
    return {
        "messages": [message],
        "current_agent": "clinical"
    }

