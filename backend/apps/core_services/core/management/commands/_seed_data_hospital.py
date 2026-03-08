"""
Dữ liệu seed: Thuốc, Xét nghiệm, CĐHA, Nội trú, Billing, QMS, DMKT
"""
from datetime import date, timedelta

# ======================== DRUG CATEGORIES + MEDICATIONS ========================

DRUG_CATEGORIES = [
    "Kháng sinh", "Giảm đau - Hạ sốt", "Tim mạch - Huyết áp",
    "Tiêu hóa - Dạ dày", "Hô hấp", "Thần kinh - Tâm thần",
    "Nội tiết - Đái tháo đường", "Kháng viêm - Corticoid",
    "Vitamin - Khoáng chất", "Dịch truyền",
]

# (category, code, name, active_ingredient, strength, dosage_form, route, unit, purchase, sell, requires_rx)
MEDICATIONS = [
    ("Kháng sinh", "MED-AB01", "Amoxicillin 500mg", "Amoxicillin", "500mg", "Viên nang", "Uống", "Viên", 800, 1500, True),
    ("Kháng sinh", "MED-AB02", "Azithromycin 500mg", "Azithromycin", "500mg", "Viên nén", "Uống", "Viên", 3000, 5500, True),
    ("Kháng sinh", "MED-AB03", "Ceftriaxone 1g", "Ceftriaxone", "1g", "Bột pha tiêm", "Tiêm", "Lọ", 12000, 22000, True),
    ("Giảm đau - Hạ sốt", "MED-GD01", "Paracetamol 500mg", "Paracetamol", "500mg", "Viên nén", "Uống", "Viên", 200, 500, False),
    ("Giảm đau - Hạ sốt", "MED-GD02", "Ibuprofen 400mg", "Ibuprofen", "400mg", "Viên nén", "Uống", "Viên", 300, 700, False),
    ("Giảm đau - Hạ sốt", "MED-GD03", "Diclofenac 75mg", "Diclofenac", "75mg", "Viên nén", "Uống", "Viên", 500, 1000, True),
    ("Tim mạch - Huyết áp", "MED-TM01", "Amlodipine 5mg", "Amlodipine", "5mg", "Viên nén", "Uống", "Viên", 400, 900, True),
    ("Tim mạch - Huyết áp", "MED-TM02", "Losartan 50mg", "Losartan", "50mg", "Viên nén", "Uống", "Viên", 600, 1200, True),
    ("Tim mạch - Huyết áp", "MED-TM03", "Atorvastatin 20mg", "Atorvastatin", "20mg", "Viên nén", "Uống", "Viên", 1000, 2000, True),
    ("Tiêu hóa - Dạ dày", "MED-TH01", "Omeprazole 20mg", "Omeprazole", "20mg", "Viên nang", "Uống", "Viên", 600, 1200, True),
    ("Tiêu hóa - Dạ dày", "MED-TH02", "Domperidone 10mg", "Domperidone", "10mg", "Viên nén", "Uống", "Viên", 300, 600, True),
    ("Tiêu hóa - Dạ dày", "MED-TH03", "Smecta 3g", "Diosmectite", "3g", "Gói bột", "Uống", "Gói", 1500, 3000, False),
    ("Hô hấp", "MED-HH01", "Salbutamol 2mg", "Salbutamol", "2mg", "Viên nén", "Uống", "Viên", 200, 500, True),
    ("Hô hấp", "MED-HH02", "Acetylcysteine 200mg", "Acetylcysteine", "200mg", "Gói cốm", "Uống", "Gói", 800, 1500, False),
    ("Thần kinh - Tâm thần", "MED-TK01", "Diazepam 5mg", "Diazepam", "5mg", "Viên nén", "Uống", "Viên", 300, 600, True),
    ("Nội tiết - Đái tháo đường", "MED-NT01", "Metformin 850mg", "Metformin", "850mg", "Viên nén", "Uống", "Viên", 400, 800, True),
    ("Nội tiết - Đái tháo đường", "MED-NT02", "Insulin Lantus", "Insulin Glargine", "100IU/mL", "Bút tiêm", "Tiêm", "Bút", 180000, 350000, True),
    ("Kháng viêm - Corticoid", "MED-KV01", "Methylprednisolone 16mg", "Methylprednisolone", "16mg", "Viên nén", "Uống", "Viên", 2000, 4000, True),
    ("Vitamin - Khoáng chất", "MED-VT01", "Vitamin C 500mg", "Acid Ascorbic", "500mg", "Viên nén", "Uống", "Viên", 100, 300, False),
    ("Vitamin - Khoáng chất", "MED-VT02", "Calcium-D 600mg", "Calcium + Vitamin D3", "600mg/400IU", "Viên nén", "Uống", "Viên", 200, 500, False),
    ("Dịch truyền", "MED-DT01", "NaCl 0.9% 500mL", "Natri Chloride", "0.9%", "Dung dịch truyền", "Truyền TM", "Chai", 8000, 15000, True),
    ("Dịch truyền", "MED-DT02", "Glucose 5% 500mL", "Glucose", "5%", "Dung dịch truyền", "Truyền TM", "Chai", 7000, 13000, True),
]

# Mỗi thuốc tạo 1 lô
def get_lot_data():
    today = date.today()
    return {
        "lot_number_prefix": "LOT",
        "manufacture_date": today - timedelta(days=60),
        "expiry_date": today + timedelta(days=365),
        "import_date": today - timedelta(days=30),
        "initial_quantity": 500,
        "supplier": "Công ty Dược phẩm Trung Ương",
    }

# ======================== LAB ========================

LAB_CATEGORIES = [
    ("Huyết học", "Xét nghiệm tế bào máu, đông máu"),
    ("Sinh hóa", "Xét nghiệm chức năng gan, thận, đường, lipid"),
    ("Vi sinh", "Nuôi cấy, kháng sinh đồ, PCR"),
    ("Miễn dịch - Huyết thanh", "Xét nghiệm miễn dịch, marker ung thư"),
]

# (category, code, name, unit, lower, upper, turnaround_min, price)
LAB_TESTS = [
    ("Huyết học", "HH-CTM", "Công thức máu (CBC)", "10^9/L", None, None, 30, 50000),
    ("Huyết học", "HH-PT", "Prothrombin Time (PT)", "giây", 11, 13.5, 45, 80000),
    ("Huyết học", "HH-APTT", "APTT", "giây", 25, 35, 45, 80000),
    ("Huyết học", "HH-FIB", "Fibrinogen", "g/L", 2, 4, 60, 90000),
    ("Sinh hóa", "SH-GLU", "Glucose máu", "mmol/L", 3.9, 6.1, 30, 30000),
    ("Sinh hóa", "SH-URE", "Ure máu", "mmol/L", 2.5, 7.5, 30, 30000),
    ("Sinh hóa", "SH-CREA", "Creatinine máu", "µmol/L", 62, 106, 30, 35000),
    ("Sinh hóa", "SH-AST", "AST (SGOT)", "U/L", 0, 40, 30, 35000),
    ("Sinh hóa", "SH-ALT", "ALT (SGPT)", "U/L", 0, 41, 30, 35000),
    ("Sinh hóa", "SH-CHOL", "Cholesterol toàn phần", "mmol/L", 0, 5.2, 30, 40000),
    ("Sinh hóa", "SH-TRIG", "Triglyceride", "mmol/L", 0, 1.7, 30, 40000),
    ("Sinh hóa", "SH-HBA1C", "HbA1c", "%", 4, 6, 60, 120000),
    ("Sinh hóa", "SH-CRP", "C-Reactive Protein (CRP)", "mg/L", 0, 5, 45, 80000),
    ("Vi sinh", "VS-CTM", "Cấy máu", None, None, None, 2880, 200000),
    ("Vi sinh", "VS-CTN", "Cấy nước tiểu", None, None, None, 2880, 150000),
    ("Vi sinh", "VS-COVID", "SARS-CoV-2 RT-PCR", None, None, None, 240, 350000),
    ("Miễn dịch - Huyết thanh", "MD-HBSAG", "HBsAg (Viêm gan B)", None, None, None, 60, 100000),
    ("Miễn dịch - Huyết thanh", "MD-ANTIHCV", "Anti-HCV (Viêm gan C)", None, None, None, 60, 120000),
    ("Miễn dịch - Huyết thanh", "MD-HIV", "HIV Ag/Ab", None, None, None, 60, 100000),
    ("Miễn dịch - Huyết thanh", "MD-PSA", "PSA (Marker tiền liệt tuyến)", "ng/mL", 0, 4, 120, 200000),
]

# ======================== IMAGING ========================

# (code, name, description, turnaround_min)
MODALITIES = [
    ("XQ", "X-Quang", "Chụp X-Quang kỹ thuật số (DR)", 15),
    ("CT", "CT Scanner", "Chụp cắt lớp vi tính đa lát cắt", 30),
    ("MRI", "MRI", "Chụp cộng hưởng từ", 45),
    ("US", "Siêu âm", "Siêu âm tổng quát và chuyên sâu", 20),
    ("DSA", "DSA", "Chụp mạch số hóa xóa nền", 60),
]

# (modality_code, code, name, price, preparation)
IMAGING_PROCEDURES = [
    ("XQ", "XQ-NGUC", "X-Quang ngực thẳng", 80000, "Không cần chuẩn bị đặc biệt"),
    ("XQ", "XQ-BUNG", "X-Quang bụng đứng", 80000, None),
    ("XQ", "XQ-COT-SONG", "X-Quang cột sống thắt lưng", 100000, None),
    ("XQ", "XQ-XUONG", "X-Quang xương chi", 80000, None),
    ("CT", "CT-SO", "CT sọ não không tiêm", 500000, "Không cần nhịn ăn"),
    ("CT", "CT-NGUC", "CT ngực có tiêm", 800000, "Nhịn ăn 4h, xét nghiệm creatinine"),
    ("CT", "CT-BUNG", "CT bụng chậu có tiêm", 900000, "Nhịn ăn 6h, uống thuốc cản quang"),
    ("MRI", "MRI-SO", "MRI sọ não", 1500000, "Không mang kim loại, nhịn ăn 4h"),
    ("MRI", "MRI-COT-SONG", "MRI cột sống thắt lưng", 1500000, None),
    ("MRI", "MRI-KHOP-GOI", "MRI khớp gối", 1200000, None),
    ("US", "US-BUNG-TQ", "Siêu âm bụng tổng quát", 150000, "Nhịn ăn 6-8h"),
    ("US", "US-TIM", "Siêu âm tim", 300000, None),
    ("US", "US-TUYEN-GIAP", "Siêu âm tuyến giáp", 150000, None),
    ("US", "US-SAN", "Siêu âm sản khoa", 200000, None),
    ("DSA", "DSA-MACH-VANH", "Chụp mạch vành", 5000000, "Nhịn ăn 6h, xét nghiệm đông máu"),
]

# ======================== INPATIENT (Ward/Room/Bed) ========================

# (department_code, ward_code, ward_name, total_beds, floor)
WARDS = [
    ("NOI_TQ", "W-NTQ", "Khoa Nội TQ - Nội trú", 30, "Tầng 3"),
    ("NOI_TM", "W-NTM", "Khoa Nội Tim Mạch - Nội trú", 20, "Tầng 3"),
    ("NGOAI_TQ", "W-NGT", "Khoa Ngoại TQ - Nội trú", 25, "Tầng 4"),
    ("NGOAI_CT", "W-NGC", "Khoa Ngoại CTCH - Nội trú", 20, "Tầng 4"),
    ("GMHS", "W-ICU", "Khoa GMHS - ICU", 10, "Tầng 2"),
]

# (ward_code, room_number, room_type, capacity, price_per_day, has_bathroom, has_ac)
ROOMS = [
    ("W-NTQ", "301", "STANDARD", 6, 150000, True, True),
    ("W-NTQ", "302", "STANDARD", 6, 150000, True, True),
    ("W-NTQ", "303", "VIP", 2, 500000, True, True),
    ("W-NTM", "311", "STANDARD", 4, 200000, True, True),
    ("W-NTM", "312", "VIP", 2, 600000, True, True),
    ("W-NGT", "401", "STANDARD", 6, 150000, True, True),
    ("W-NGT", "402", "STANDARD", 6, 150000, True, True),
    ("W-NGC", "411", "STANDARD", 4, 200000, True, True),
    ("W-NGC", "412", "STANDARD", 4, 200000, True, True),
    ("W-ICU", "201-ICU", "ICU", 2, 2000000, True, True),
    ("W-ICU", "202-ICU", "ICU", 2, 2000000, True, True),
]

# ======================== QMS - SERVICE STATIONS ========================

# (code, name, station_type, department_code, room_location)
SERVICE_STATIONS = [
    ("TD01", "Quầy Tiếp Đón 1", "RECEPTION", None, "Tầng 1 - Sảnh chính"),
    ("TD02", "Quầy Tiếp Đón 2", "RECEPTION", None, "Tầng 1 - Sảnh chính"),
    ("PL01", "Bàn Phân Luồng 1", "TRIAGE", None, "Tầng 1 - Sau tiếp đón"),
    ("PK01", "Phòng Khám Nội TQ - 1", "DOCTOR", "NOI_TQ", "Tầng 2 - Dãy A"),
    ("PK02", "Phòng Khám Nội TQ - 2", "DOCTOR", "NOI_TQ", "Tầng 2 - Dãy A"),
    ("PK03", "Phòng Khám Tim Mạch", "DOCTOR", "NOI_TM", "Tầng 2 - Dãy A"),
    ("PK04", "Phòng Khám Tiêu Hóa", "DOCTOR", "NOI_TH", "Tầng 2 - Dãy B"),
    ("PK05", "Phòng Khám Hô Hấp", "DOCTOR", "NOI_HH", "Tầng 2 - Dãy B"),
    ("PK06", "Phòng Khám Thần Kinh", "DOCTOR", "NOI_TK", "Tầng 2 - Dãy B"),
    ("PK07", "Phòng Khám Nội Tiết", "DOCTOR", "NOI_NT", "Tầng 2 - Dãy C"),
    ("PK08", "Phòng Khám Ngoại TQ", "DOCTOR", "NGOAI_TQ", "Tầng 2 - Dãy C"),
    ("PK09", "Phòng Khám CTCH", "DOCTOR", "NGOAI_CT", "Tầng 2 - Dãy C"),
    ("PK10", "Phòng Khám Sản", "DOCTOR", "SAN", "Tầng 2 - Dãy D"),
    ("PK11", "Phòng Khám Nhi", "DOCTOR", "NHI", "Tầng 2 - Dãy D"),
    ("PK12", "Phòng Khám TMH", "DOCTOR", "TMH", "Tầng 2 - Dãy D"),
    ("PK13", "Phòng Khám RHM", "DOCTOR", "RHM", "Tầng 2 - Dãy E"),
    ("PK14", "Phòng Khám Mắt", "DOCTOR", "MAT", "Tầng 2 - Dãy E"),
    ("PK15", "Phòng Khám Da Liễu", "DOCTOR", "DALIEU", "Tầng 2 - Dãy E"),
    ("LIS01", "Phòng Lấy Mẫu XN 1", "LIS", "XN", "Tầng 1 - Dãy B"),
    ("LIS02", "Phòng Lấy Mẫu XN 2", "LIS", "XN", "Tầng 1 - Dãy B"),
    ("RIS01", "Phòng X-Quang", "RIS", "CDHA", "Tầng 1 - Dãy C"),
    ("RIS02", "Phòng CT/MRI", "RIS", "CDHA", "Tầng 1 - Dãy C"),
    ("RIS03", "Phòng Siêu Âm", "RIS", "CDHA", "Tầng 1 - Dãy C"),
    ("PHARMA01", "Nhà Thuốc 1", "PHARMACY", "DUOC", "Tầng 1 - Sảnh chính"),
    ("CASH01", "Quầy Thu Ngân 1", "CASHIER", None, "Tầng 1 - Sảnh chính"),
    ("CASH02", "Quầy Thu Ngân 2", "CASHIER", None, "Tầng 1 - Sảnh chính"),
]

# ======================== BILLING ========================

PRICE_LISTS = [
    ("BG-THUONG", "Bảng giá Dịch vụ Thường", True, True),
    ("BG-BHYT", "Bảng giá BHYT", False, True),
    ("BG-VIP", "Bảng giá VIP", False, True),
]

# (code, name, service_type, base_price, bhyt_code, bhyt_price)
SERVICE_CATALOG = [
    ("DV-KHAM-TQ", "Khám bệnh tổng quát", "CONSULTATION", 100000, "KCB-01", 30000),
    ("DV-KHAM-CK", "Khám chuyên khoa", "CONSULTATION", 150000, "KCB-02", 40000),
    ("DV-KHAM-CC", "Khám cấp cứu", "CONSULTATION", 200000, "KCB-03", 50000),
    ("DV-XN-CTM", "Xét nghiệm công thức máu", "LAB", 50000, "XN-001", 35000),
    ("DV-XN-SH", "Xét nghiệm sinh hóa máu", "LAB", 80000, "XN-002", 55000),
    ("DV-XQ-NGUC", "Chụp X-Quang ngực", "IMAGING", 80000, "CDHA-01", 50000),
    ("DV-CT-SO", "CT sọ não", "IMAGING", 500000, "CDHA-02", 350000),
    ("DV-MRI-SO", "MRI sọ não", "IMAGING", 1500000, "CDHA-03", 900000),
    ("DV-SA-BUNG", "Siêu âm bụng", "IMAGING", 150000, "CDHA-04", 80000),
    ("DV-TTHUOC", "Thủ thuật tiểu phẫu", "PROCEDURE", 300000, "PT-001", 150000),
    ("DV-GIUONG-TH", "Giường bệnh thường/ngày", "BED", 150000, "GN-001", 100000),
    ("DV-GIUONG-VIP", "Giường bệnh VIP/ngày", "BED", 500000, None, None),
    ("DV-GIUONG-ICU", "Giường ICU/ngày", "BED", 2000000, "GN-003", 1500000),
]

# ======================== TECHNICAL SERVICES (DMKT) ========================

# (code, name, group, unit, unit_price, bhyt_price, is_bhyt)
TECHNICAL_SERVICES = [
    ("DMKT-KCB-01", "Khám bệnh", "KCB", "lần", 100000, 30000, True),
    ("DMKT-KCB-02", "Khám chuyên khoa", "KCB", "lần", 150000, 40000, True),
    ("DMKT-XN-01", "Công thức máu (CBC)", "XN", "lần", 50000, 35000, True),
    ("DMKT-XN-02", "Sinh hóa máu 10 chỉ số", "XN", "lần", 150000, 100000, True),
    ("DMKT-XN-03", "Tổng phân tích nước tiểu", "XN", "lần", 40000, 25000, True),
    ("DMKT-XN-04", "Xét nghiệm HbA1c", "XN", "lần", 120000, 80000, True),
    ("DMKT-CDHA-01", "X-Quang thường quy (1 phim)", "CDHA", "lần", 80000, 50000, True),
    ("DMKT-CDHA-02", "CT Scanner 64 lát cắt không tiêm", "CDHA", "lần", 500000, 350000, True),
    ("DMKT-CDHA-03", "CT Scanner 64 lát cắt có tiêm", "CDHA", "lần", 800000, 550000, True),
    ("DMKT-CDHA-04", "MRI 1.5 Tesla", "CDHA", "lần", 1500000, 900000, True),
    ("DMKT-CDHA-05", "Siêu âm ổ bụng", "CDHA", "lần", 150000, 80000, True),
    ("DMKT-CDHA-06", "Siêu âm tim", "CDHA", "lần", 300000, 200000, True),
    ("DMKT-PT-01", "Phẫu thuật mổ ruột thừa", "PT", "lần", 3000000, 2000000, True),
    ("DMKT-PT-02", "Phẫu thuật nội soi sỏi mật", "PT", "lần", 5000000, 3500000, True),
    ("DMKT-PHCN-01", "Vật lý trị liệu (1 buổi)", "PHCN", "buổi", 100000, 60000, True),
]
