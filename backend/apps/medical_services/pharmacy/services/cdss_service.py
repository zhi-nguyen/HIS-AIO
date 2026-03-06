"""
CDSSService – Clinical Decision Support System (Hỗ trợ quyết định lâm sàng).

Track 3: Cảnh báo dị ứng + tương tác thuốc khi kê đơn.
Được gọi từ pharmacist_agent, view CDSS API, và signal sau khi tạo Prescription.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apps.core_services.patients.allergy import PatientAllergy
from apps.medical_services.pharmacy.drug_interactions import DrugInteraction

if TYPE_CHECKING:
    from apps.medical_services.pharmacy.models import Prescription

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Cấu trúc cảnh báo chuẩn (giống nhau cho allergy và interaction)
# ─────────────────────────────────────────────────────────────────────────────

def _allergy_alert(allergy: PatientAllergy, matched_ingredient: str) -> dict:
    return {
        'type': 'ALLERGY',
        'severity': allergy.severity,
        'allergen': allergy.allergen_name,
        'matched_ingredient': matched_ingredient,
        'reaction': allergy.reaction_description or 'Không có mô tả',
        'message': (
            f"⚠️ CẢNH BÁO DỊ ỨNG [{allergy.get_severity_display()}]: "
            f"Bệnh nhân có tiền sử dị ứng với '{allergy.allergen_name}'. "
            f"Thuốc đang kê chứa hoạt chất '{matched_ingredient}' có thể gây phản ứng."
        ),
        'is_critical': allergy.severity in ('SEVERE', 'LIFE_THREATENING'),
    }


def _interaction_alert(interaction: DrugInteraction) -> dict:
    return {
        'type': 'INTERACTION',
        'severity': interaction.severity,
        'drug_a': interaction.drug_a_name,
        'drug_b': interaction.drug_b_name,
        'description': interaction.description,
        'recommendation': interaction.recommendation,
        'message': (
            f"⚠️ TƯƠNG TÁC THUỐC [{interaction.get_severity_display()}]: "
            f"{interaction.drug_a_name} + {interaction.drug_b_name}. "
            f"{interaction.recommendation}"
        ),
        'is_critical': interaction.severity == 'MAJOR',
    }


# ─────────────────────────────────────────────────────────────────────────────
# Service chính
# ─────────────────────────────────────────────────────────────────────────────

class CDSSService:
    """Hệ thống hỗ trợ quyết định lâm sàng – kiểm tra dị ứng và tương tác thuốc."""

    @staticmethod
    def check_allergy_alert(patient_id: str, active_ingredients: list[str]) -> list[dict]:
        """
        So sánh danh sách hoạt chất với dị ứng đã ghi nhận của bệnh nhân.

        Args:
            patient_id: UUID của bệnh nhân (str).
            active_ingredients: Danh sách tên hoạt chất (viết thường hoặc bất kỳ).

        Returns:
            Danh sách cảnh báo dị ứng (rỗng nếu an toàn).
        """
        if not active_ingredients:
            return []

        normalized_ingredients = {ing.lower().strip() for ing in active_ingredients}

        try:
            allergies = PatientAllergy.objects.filter(
                patient_id=patient_id,
                allergen_type=PatientAllergy.AllergenType.DRUG,
                is_active=True,
            ).select_related('confirmed_by')
        except Exception as e:
            logger.error(f"CDSSService.check_allergy_alert error: {e}")
            return []

        alerts = []
        for allergy in allergies:
            allergen_norm = allergy.allergen_name_normalized
            # So sánh: tên dị nguyên có chứa trong bất kỳ hoạt chất nào không
            # (và ngược lại, để bắt cả "Amoxicillin" khi dị nguyên là "Penicillin")
            for ingredient in normalized_ingredients:
                if allergen_norm in ingredient or ingredient in allergen_norm:
                    alerts.append(_allergy_alert(allergy, ingredient))
                    break  # Đã match rồi, không cần check tiếp với allergy này

        return alerts

    @staticmethod
    def check_drug_interaction(active_ingredients: list[str]) -> list[dict]:
        """
        Tìm tương tác giữa tất cả các hoạt chất trong đơn thuốc.

        Args:
            active_ingredients: Danh sách tên hoạt chất.

        Returns:
            Danh sách cảnh báo tương tác (rỗng nếu an toàn).
        """
        if len(active_ingredients) < 2:
            return []

        try:
            interactions = DrugInteraction.find_interactions(active_ingredients)
            return [_interaction_alert(i) for i in interactions]
        except Exception as e:
            logger.error(f"CDSSService.check_drug_interaction error: {e}")
            return []

    @staticmethod
    def run_cdss_check(prescription_id: str) -> dict:
        """
        Tổng hợp kiểm tra CDSS đầy đủ cho một đơn thuốc.

        Lấy thông tin đơn thuốc → trích active_ingredients → check dị ứng + tương tác.
        Kết quả được lưu vào Prescription.cdss_alerts.

        Args:
            prescription_id: UUID của Prescription.

        Returns:
            {
                'allergy_alerts': [...],
                'interaction_alerts': [...],
                'has_critical': bool,
                'prescription_id': str,
            }
        """
        from apps.medical_services.pharmacy.models import Prescription, PrescriptionDetail

        try:
            prescription = Prescription.objects.select_related(
                'visit__patient'
            ).prefetch_related(
                'details__medication'
            ).get(id=prescription_id)
        except Prescription.DoesNotExist:
            logger.warning(f"CDSSService: Prescription {prescription_id} not found")
            return {
                'allergy_alerts': [],
                'interaction_alerts': [],
                'has_critical': False,
                'prescription_id': str(prescription_id),
                'error': 'Prescription not found',
            }

        # Thu thập active_ingredients từ chi tiết đơn thuốc
        active_ingredients = []
        for detail in prescription.details.all():
            med = detail.medication
            if med.active_ingredient:
                active_ingredients.append(med.active_ingredient)

        patient_id = str(prescription.visit.patient_id)

        # Chạy 2 loại kiểm tra
        allergy_alerts = CDSSService.check_allergy_alert(patient_id, active_ingredients)
        interaction_alerts = CDSSService.check_drug_interaction(active_ingredients)

        has_critical = any(a['is_critical'] for a in allergy_alerts + interaction_alerts)

        result = {
            'allergy_alerts': allergy_alerts,
            'interaction_alerts': interaction_alerts,
            'has_critical': has_critical,
            'prescription_id': str(prescription_id),
        }

        # Lưu kết quả vào field cdss_alerts của Prescription
        try:
            prescription.cdss_alerts = result
            prescription.save(update_fields=['cdss_alerts', 'updated_at'])
        except Exception as e:
            logger.error(f"CDSSService: Failed to save cdss_alerts to prescription: {e}")

        logger.info(
            f"CDSS check for prescription {prescription_id}: "
            f"{len(allergy_alerts)} allergy alerts, "
            f"{len(interaction_alerts)} interaction alerts, "
            f"critical={has_critical}"
        )

        return result
