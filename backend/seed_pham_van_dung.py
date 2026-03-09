"""
Seed script: Tạo hồ sơ bệnh án giả cho bệnh nhân Phạm Văn Dụng
CCCD: 079055004321 | Hưu trí | Sinh 10/02/1955 | Nam

Chạy:
  python seed_pham_van_dung.py

Kết quả:
  - Tạo/tìm Patient (Phạm Văn Dụng)
  - Tạo 4 lượt khám cũ (COMPLETED) với hồ sơ bệnh án đầy đủ
  - Bệnh nền: Tăng huyết áp, Đái tháo đường type 2, Gout mạn tính
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django.setup()

from datetime import date, datetime, timedelta
from django.utils import timezone
from django.db import transaction

from apps.core_services.patients.models import Patient
from apps.core_services.reception.models import Visit
from apps.core_services.departments.models import Department
from apps.medical_services.emr.models import ClinicalRecord


# ============================================================
# Dữ liệu seed
# ============================================================

PATIENT_DATA = {
    "id_card": "079055004321",
    "insurance_number": "HT7920000001234",
    "first_name": "Dụng",
    "last_name": "Phạm Văn",
    "date_of_birth": date(1955, 2, 10),
    "gender": "M",
}

# 4 lượt khám với bệnh án đầy đủ (gần → xa, completed)
VISIT_RECORDS = [
    {
        # --- Lượt khám 1: 3 tháng trước (Nội Tim Mạch — THA vào cơn) ---
        "days_ago": 90,
        "dept_code": "NOI_TM",
        "chief_complaint": "Đau đầu dữ dội vùng chẩm, hoa mắt, chóng mặt, huyết áp tăng cao. Bệnh nhân tự đo HA tại nhà đo được 185/110 mmHg.",
        "history": (
            "Bệnh nhân nam 70 tuổi, tiền sử THA 15 năm, đang điều trị Amlodipine 5mg/ngày và Losartan 50mg/ngày. "
            "Sáng nay thức dậy thấy đau đầu vùng chẩm dữ dội, buồn nôn, nhìn mờ thoáng qua. "
            "Tự kiểm tra HA tại nhà: 185/110 mmHg. Không có triệu chứng yếu liệt, nói khó, méo miệng. "
            "Bệnh nhân đến cấp cứu ngay."
        ),
        "physical_exam": (
            "Toàn thân: Tỉnh, tiếp xúc tốt. Da niêm mạc hồng.\n"
            "Sinh hiệu: M 88 lần/phút, HA 182/108 mmHg, SpO2 97%, Nhiệt độ 37.1°C, Nhịp thở 18/phút.\n"
            "Tim: Nhịp tim đều, tiếng tim rõ, không nghe âm thổi. T2 mạnh ở đáy.\n"
            "Phổi: Trong, không ral.\n"
            "Bụng: Mềm, không đau.\n"
            "Thần kinh: Không có dấu hiệu thần kinh cục bộ. GCS 15.\n"
            "Đáy mắt: Dấu hiệu AV nicking, không có phù gai."
        ),
        "vital_signs": {
            "heart_rate": 88,
            "bp_systolic": 182,
            "bp_diastolic": 108,
            "spo2": 97,
            "temperature": 37.1,
            "respiratory_rate": 18,
        },
        "final_diagnosis": (
            "1. Cơn tăng huyết áp (Hypertensive urgency) - không biến chứng ngay\n"
            "2. Tăng huyết áp nguyên phát độ 3 (THA mạn tính kiểm soát kém)\n"
            "3. Đái tháo đường type 2 (theo dõi)"
        ),
        "treatment": (
            "1. Nifedipine 10mg ngậm dưới lưỡi → Theo dõi HA mỗi 15 phút\n"
            "2. Nghỉ ngơi tuyệt đối, hạn chế muối\n"
            "3. Điều chỉnh thuốc: Tăng Amlodipine lên 10mg/ngày, thêm Indapamide 1.5mg/ngày\n"
            "4. Theo dõi tại phòng cấp cứu 4 giờ, HA kiểm soát xuống 155/90 mmHg → Cho về\n"
            "5. Hẹn tái khám Nội Tim Mạch sau 2 tuần\n"
            "6. Tư vấn: Không tự ý ngưng thuốc, chế độ ăn DASH, theo dõi HA ngày 2 lần"
        ),
        "triage_code": "CODE_RED",
    },
    {
        # --- Lượt khám 2: 6 tháng trước (Nội Tiết — ĐTĐ2, HbA1c cao) ---
        "days_ago": 180,
        "dept_code": "NOI_NT",
        "chief_complaint": "Khát nước nhiều, tiểu nhiều, mệt mỏi. Đường huyết tự đo buổi sáng 12–14 mmol/L suốt 2 tuần.",
        "history": (
            "Bệnh nhân nam 70 tuổi, ĐTĐ type 2 phát hiện 8 năm, đang điều trị Metformin 1000mg x 2 lần/ngày và Glipizide 5mg/ngày. "
            "Trong 2 tuần gần đây đường huyết buổi sáng liên tục cao 12–14 mmol/L dù không thay đổi chế độ ăn. "
            "Cảm giác mệt mỏi, khát nước nhiều, tiểu 8–10 lần/ngày. "
            "Tê bì nhẹ hai bàn chân, không có vết thương bàn chân."
        ),
        "physical_exam": (
            "Toàn thân: Tỉnh, tiếp xúc tốt. BMI ước tính khoảng 27 kg/m². Da niêm mạc hồng.\n"
            "Sinh hiệu: M 76/phút, HA 148/88 mmHg (đang điều trị THA), SpO2 98%, T 36.8°C.\n"
            "Tim phổi: Bình thường.\n"
            "Bụng: Mềm, không đau. Gan lách không sờ thấy.\n"
            "Chi dưới: Không phù. Mạch mu chân rõ 2 bên.\n"
            "Thần kinh ngoại biên: Giảm cảm giác rung nhẹ ở ngón 1 bàn chân T khi thử monofilament 10g."
        ),
        "vital_signs": {
            "heart_rate": 76,
            "bp_systolic": 148,
            "bp_diastolic": 88,
            "spo2": 98,
            "temperature": 36.8,
            "weight": 72,
            "height": 165,
        },
        "final_diagnosis": (
            "1. Đái tháo đường type 2 kiểm soát kém (HbA1c 9.2%)\n"
            "2. Biến chứng thần kinh ngoại biên đái tháo đường (giai đoạn sớm)\n"
            "3. Tăng huyết áp nguyên phát (trong điều trị)"
        ),
        "treatment": (
            "1. Thêm Sitagliptin 100mg/ngày (DPP-4 inhibitor)\n"
            "2. Giữ Metformin 1000mg x 2 lần/ngày\n"
            "3. Tăng Glipizide lên 10mg/ngày, uống trước ăn sáng 30 phút\n"
            "4. Tư vấn chế độ ăn kiểm soát carbohydrate, mục tiêu đường huyết đói < 7 mmol/L\n"
            "5. Kiểm tra bàn chân mỗi ngày, mang giày vừa vặn\n"
            "6. Hẹn tái khám sau 3 tháng, kiểm tra HbA1c, chức năng thận\n"
            "7. Chuyển khám Mắt để sàng lọc bệnh võng mạc ĐTĐ"
        ),
        "triage_code": "CODE_GREEN",
    },
    {
        # --- Lượt khám 3: 1 năm trước (Ngoại Tổng Quát — Gout cấp khớp gối P) ---
        "days_ago": 365,
        "dept_code": "NGOAI_TQ",
        "chief_complaint": "Sưng đỏ nóng khớp gối phải đột ngột, đau dữ dội không đi được, khởi phát đêm qua sau bữa tiệc.",
        "history": (
            "Bệnh nhân nam 70 tuổi, tiền sử Gout mạn tính 5 năm, đang điều trị Allopurinol 300mg/ngày. "
            "Tối hôm qua dự đám giỗ có ăn thịt đỏ và cá biển, uống bia. "
            "Đêm khuya đột ngột đau dữ dội khớp gối phải, không chịu được. Sáng ra khớp gối P sưng to, đỏ, nóng rát, không đứng được. "
            "Lần cuối cơn Gout cấp là 8 tháng trước (khớp ngón chân cái T)."
        ),
        "physical_exam": (
            "Toàn thân: Tỉnh, đau, đi khập khiễng.\n"
            "Sinh hiệu: M 90/phút, HA 155/92 mmHg, SpO2 98%, T 37.4°C.\n"
            "Khớp gối P: Sưng rõ, da đỏ ửng, nóng, ấn đau +++, hạn chế vận động hoàn toàn. Không có tophy rõ ràng quanh khớp.\n"
            "Khớp gối T: Bình thường.\n"
            "Bàn chân T: Sẹo cũ vùng ngón 1, không có cơn cấp hiện tại.\n"
            "Xét nghiệm: Uric acid huyết thanh: 520 μmol/L. BC 11.2 x10^9/L, CRP 45 mg/L, ESR 58 mm/h."
        ),
        "vital_signs": {
            "heart_rate": 90,
            "bp_systolic": 155,
            "bp_diastolic": 92,
            "spo2": 98,
            "temperature": 37.4,
            "respiratory_rate": 18,
        },
        "final_diagnosis": (
            "1. Viêm khớp Gout cấp — khớp gối phải\n"
            "2. Tăng uric acid máu (520 μmol/L)\n"
            "3. Gout mạn tính — đợt cấp\n"
            "4. Kèm: THA + ĐTĐ type 2"
        ),
        "treatment": (
            "1. Colchicine 0.5mg x 2 lần/ngày, dùng 7 ngày\n"
            "2. Indomethacin 25mg x 3 lần/ngày, sau ăn (thận trọng do THA)\n"
            "3. Chườm lạnh khớp gối, hạn chế vận động\n"
            "4. Tăng Allopurinol lên 400mg/ngày sau khi hết cơn cấp (2 tuần)\n"
            "5. Tuyệt đối kiêng: thịt đỏ, nội tạng, hải sản, bia rượu\n"
            "6. Uống nhiều nước > 2L/ngày\n"
            "7. Hẹn tái khám sau 2 tuần kiểm tra uric acid"
        ),
        "triage_code": "CODE_YELLOW",
    },
    {
        # --- Lượt khám 4: 18 tháng trước (Nội Tổng Quát — tái khám định kỳ) ---
        "days_ago": 540,
        "dept_code": "NOI_TQ",
        "chief_complaint": "Tái khám định kỳ 3 tháng. Bệnh nhân không có triệu chứng cấp tính. Kiểm tra tiến triển THA, ĐTĐ2, Gout.",
        "history": (
            "Bệnh nhân nam 69 tuổi đến tái khám định kỳ theo lịch hẹn. "
            "HA kiểm soát tốt hơn, tự đo buổi sáng khoảng 135–145/80–90 mmHg. "
            "Đường huyết tự đo buổi sáng khoảng 8–10 mmol/L, chưa đạt mục tiêu nhưng cải thiện so với lần trước. "
            "Không có cơn đau khớp Gout trong 3 tháng qua. "
            "Tuân thủ thuốc tốt, chế độ ăn chưa kiểm soát hoàn toàn."
        ),
        "physical_exam": (
            "Toàn thân: Tỉnh táo, da niêm mạc hồng, BMI 27.2 kg/m².\n"
            "Sinh hiệu: M 72/phút, HA 138/85 mmHg, SpO2 98%, T 36.7°C. CN: 73kg, CC: 165cm.\n"
            "Tim: Đều, rõ, không âm thổi.\n"
            "Phổi: Trong.\n"
            "Bụng: Mềm, không đau.\n"
            "Chi dưới: Không phù. Mạch mu chân rõ.\n"
            "XN: HbA1c 8.1% (cải thiện từ 9.2%), Creatinine 1.1 mg/dL (bình thường), Uric acid 420 μmol/L."
        ),
        "vital_signs": {
            "heart_rate": 72,
            "bp_systolic": 138,
            "bp_diastolic": 85,
            "spo2": 98,
            "temperature": 36.7,
            "weight": 73,
            "height": 165,
        },
        "final_diagnosis": (
            "1. Tăng huyết áp nguyên phát — kiểm soát trung bình\n"
            "2. Đái tháo đường type 2 — HbA1c cải thiện (8.1%), chưa đạt mục tiêu\n"
            "3. Gout mạn tính — ổn định"
        ),
        "treatment": (
            "1. Tiếp tục Amlodipine 10mg, Losartan 50mg, Indapamide 1.5mg\n"
            "2. Tiếp tục Metformin 1000mg x 2, Glipizide 10mg, Sitagliptin 100mg\n"
            "3. Tiếp tục Allopurinol 400mg/ngày\n"
            "4. Tư vấn chế độ ăn, tập thể dục nhẹ nhàng 30p/ngày\n"
            "5. Hẹn tái khám sau 3 tháng, kiểm tra HbA1c, lipid máu, chức năng thận"
        ),
        "triage_code": "CODE_GREEN",
    },
]


# ============================================================
# Helpers
# ============================================================

def get_or_create_patient() -> Patient:
    """Tìm hoặc tạo Patient Phạm Văn Dụng từ CCCD."""
    patient, created = Patient.objects.get_or_create(
        id_card=PATIENT_DATA["id_card"],
        defaults={
            "insurance_number": PATIENT_DATA["insurance_number"],
            "first_name": PATIENT_DATA["first_name"],
            "last_name": PATIENT_DATA["last_name"],
            "date_of_birth": PATIENT_DATA["date_of_birth"],
            "gender": PATIENT_DATA["gender"],
            "patient_code": f"BN-SEED-PVD",
        }
    )
    if created:
        print(f"  ✅ Tạo Patient mới: {patient.full_name} ({patient.patient_code})")
    else:
        print(f"  ℹ️  Patient đã tồn tại: {patient.full_name} ({patient.patient_code})")
    return patient


def get_dept(code: str) -> Department | None:
    dept = Department.objects.filter(code=code, is_active=True).first()
    if not dept:
        print(f"  ⚠️  Không tìm thấy Department code={code}, bỏ qua liên kết khoa.")
    return dept


def make_visit_code(i: int) -> str:
    return f"V-SEED-PVD-{i:02d}"


# ============================================================
# Main seed
# ============================================================

@transaction.atomic
def seed():
    print("\n=== SEED: Hồ sơ bệnh án Phạm Văn Dụng ===\n")

    patient = get_or_create_patient()
    print()

    for i, rec in enumerate(VISIT_RECORDS, 1):
        visit_code = make_visit_code(i)
        days_ago = rec["days_ago"]
        visit_date = timezone.now() - timedelta(days=days_ago)

        dept = get_dept(rec["dept_code"])

        # --- Tạo hoặc skip Visit ---
        if Visit.objects.filter(visit_code=visit_code).exists():
            print(f"  ℹ️  Visit {visit_code} đã tồn tại, bỏ qua.")
            continue

        visit = Visit.objects.create(
            visit_code=visit_code,
            patient=patient,
            status=Visit.Status.COMPLETED,
            priority=Visit.Priority.NORMAL,
            check_in_time=visit_date,
            check_out_time=visit_date + timedelta(hours=2),
            chief_complaint=rec["chief_complaint"],
            vital_signs=rec["vital_signs"],
            triage_code=rec["triage_code"],
            triage_confidence=85,
            triage_method="AI",
            confirmed_department=dept,
            recommended_department=dept,
            triage_confirmed_at=visit_date + timedelta(minutes=15),
            queue_number=i + 100,
        )

        # --- Tạo ClinicalRecord ---
        clinical = ClinicalRecord.objects.create(
            visit=visit,
            chief_complaint=rec["chief_complaint"],
            history_of_present_illness=rec["history"],
            physical_exam=rec["physical_exam"],
            vital_signs=rec["vital_signs"],
            final_diagnosis=rec["final_diagnosis"],
            treatment_plan=rec["treatment"],
            medical_summary=(
                f"BN nam {2026 - 1955} tuổi, tiền sử THA + ĐTĐ2 + Gout mạn. "
                f"Đến khám lần này: {rec['chief_complaint'][:80]}... "
                f"Kết quả: {rec['final_diagnosis'].split(chr(10))[0]}"
            ),
            is_finalized=True,
        )

        print(
            f"  ✅ [{i}] Visit {visit_code} | -{days_ago}ngày | "
            f"Khoa: {dept.code if dept else rec['dept_code']} | "
            f"Triage: {rec['triage_code']}"
        )

    print(f"\n=== Hoàn thành seed! Tổng {len(VISIT_RECORDS)} lượt khám cũ cho {patient.full_name} ===")
    print(f"\n📌 Để test kiosk: Quét CCCD '{PATIENT_DATA['id_card']}' tại /kiosk\n")


if __name__ == "__main__":
    seed()
