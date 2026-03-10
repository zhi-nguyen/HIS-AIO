"""
Seed data cho danh mục dịch vụ CLS (Cận Lâm Sàng).
Chạy: python manage.py shell < apps/core_services/core/management/commands/_seed_data_cls.py
Hoặc:  python manage.py shell -c "exec(open('apps/core_services/core/management/commands/_seed_data_cls.py').read())"
"""

from apps.medical_services.paraclinical.models import ServiceList

SERVICES = [
    # ==========================================
    # ── HUYẾT HỌC (HEMATOLOGY) ──
    # ==========================================
    {"code": "XN-HH-001", "name": "Tổng phân tích tế bào máu (25 thông số)", "price": 65000, "category": "Huyết học"},
    {"code": "XN-HH-002", "name": "Tổng phân tích tế bào máu (18 thông số)", "price": 50000, "category": "Huyết học"},
    {"code": "XN-HH-003", "name": "Kháng nguyên nhóm máu ABO, Rh", "price": 45000, "category": "Huyết học"},
    {"code": "XN-HH-004", "name": "Tốc độ máu lắng (VS)", "price": 30000, "category": "Huyết học"},
    {"code": "XN-HH-005", "name": "Đông máu cơ bản (PT, aPTT, Fibrinogen)", "price": 120000, "category": "Huyết học"},
    {"code": "XN-HH-006", "name": "Định lượng D-Dimer", "price": 180000, "category": "Huyết học"},
    {"code": "XN-HH-007", "name": "Thời gian máu chảy, máu đông", "price": 20000, "category": "Huyết học"},
    {"code": "XN-HH-008", "name": "Huyết đồ", "price": 80000, "category": "Huyết học"},
    {"code": "XN-HH-009", "name": "Tìm tế bào LE (Lupus Erythematosus)", "price": 60000, "category": "Huyết học"},
    {"code": "XN-HH-010", "name": "Định lượng Sắt huyết thanh", "price": 40000, "category": "Huyết học"},
    {"code": "XN-HH-011", "name": "Định lượng Ferritin", "price": 80000, "category": "Huyết học"},
    {"code": "XN-HH-012", "name": "Định lượng Transferrin", "price": 90000, "category": "Huyết học"},

    # ==========================================
    # ── SINH HÓA (BIOCHEMISTRY) ──
    # ==========================================
    {"code": "XN-SH-001", "name": "Định lượng Glucose máu", "price": 30000, "category": "Sinh hóa"},
    {"code": "XN-SH-002", "name": "Định lượng HbA1c", "price": 120000, "category": "Sinh hóa"},
    {"code": "XN-SH-003", "name": "Định lượng Creatinin", "price": 35000, "category": "Sinh hóa"},
    {"code": "XN-SH-004", "name": "AST (GOT)", "price": 30000, "category": "Sinh hóa"},
    {"code": "XN-SH-005", "name": "ALT (GPT)", "price": 30000, "category": "Sinh hóa"},
    {"code": "XN-SH-006", "name": "Cholesterol toàn phần", "price": 30000, "category": "Sinh hóa"},
    {"code": "XN-SH-007", "name": "Triglycerid", "price": 30000, "category": "Sinh hóa"},
    {"code": "XN-SH-008", "name": "Ure máu", "price": 30000, "category": "Sinh hóa"},
    {"code": "XN-SH-009", "name": "Acid Uric máu", "price": 30000, "category": "Sinh hóa"},
    {"code": "XN-SH-010", "name": "Bilirubin toàn phần", "price": 30000, "category": "Sinh hóa"},
    {"code": "XN-SH-011", "name": "Bilirubin trực tiếp", "price": 30000, "category": "Sinh hóa"},
    {"code": "XN-SH-012", "name": "Bilirubin gián tiếp", "price": 30000, "category": "Sinh hóa"},
    {"code": "XN-SH-013", "name": "Định lượng Protein toàn phần", "price": 30000, "category": "Sinh hóa"},
    {"code": "XN-SH-014", "name": "Định lượng Albumin", "price": 30000, "category": "Sinh hóa"},
    {"code": "XN-SH-015", "name": "Điện giải đồ (Na, K, Cl)", "price": 60000, "category": "Sinh hóa"},
    {"code": "XN-SH-016", "name": "Canxi toàn phần", "price": 30000, "category": "Sinh hóa"},
    {"code": "XN-SH-017", "name": "Canxi ion hóa", "price": 35000, "category": "Sinh hóa"},
    {"code": "XN-SH-018", "name": "GGT (Gamma Glutamyl Transferase)", "price": 35000, "category": "Sinh hóa"},
    {"code": "XN-SH-019", "name": "ALP (Phosphatase kiềm)", "price": 35000, "category": "Sinh hóa"},
    {"code": "XN-SH-020", "name": "Amylase máu", "price": 40000, "category": "Sinh hóa"},
    {"code": "XN-SH-021", "name": "Định lượng CRP định lượng", "price": 90000, "category": "Sinh hóa"},
    {"code": "XN-SH-022", "name": "Định lượng hs-CRP", "price": 120000, "category": "Sinh hóa"},
    {"code": "XN-SH-023", "name": "Định lượng Troponin T (hs)", "price": 250000, "category": "Sinh hóa"},
    {"code": "XN-SH-024", "name": "Định lượng NT-proBNP", "price": 300000, "category": "Sinh hóa"},
    {"code": "XN-SH-025", "name": "Tổng phân tích nước tiểu (10 thông số)", "price": 40000, "category": "Sinh hóa"},
    {"code": "XN-SH-026", "name": "Protein niệu 24h", "price": 50000, "category": "Sinh hóa"},

    # ==========================================
    # ── MIỄN DỊCH (IMMUNOLOGY) ──
    # ==========================================
    {"code": "XN-MD-001", "name": "HBsAg (Test nhanh)", "price": 60000, "category": "Miễn dịch"},
    {"code": "XN-MD-002", "name": "HBsAg (Miễn dịch hóa phát quang)", "price": 120000, "category": "Miễn dịch"},
    {"code": "XN-MD-003", "name": "Anti-HBs", "price": 120000, "category": "Miễn dịch"},
    {"code": "XN-MD-004", "name": "Anti-HCV (Test nhanh)", "price": 70000, "category": "Miễn dịch"},
    {"code": "XN-MD-005", "name": "Anti-HCV (Miễn dịch)", "price": 150000, "category": "Miễn dịch"},
    {"code": "XN-MD-006", "name": "HIV Ab (Test nhanh)", "price": 60000, "category": "Miễn dịch"},
    {"code": "XN-MD-007", "name": "HIV Ag/Ab (Elisa/ECLIA)", "price": 150000, "category": "Miễn dịch"},
    {"code": "XN-MD-008", "name": "TSH", "price": 120000, "category": "Miễn dịch"},
    {"code": "XN-MD-009", "name": "FT3", "price": 120000, "category": "Miễn dịch"},
    {"code": "XN-MD-010", "name": "FT4", "price": 120000, "category": "Miễn dịch"},
    {"code": "XN-MD-011", "name": "Beta-hCG", "price": 150000, "category": "Miễn dịch"},
    {"code": "XN-MD-012", "name": "AFP (Dấu ấn ung thư gan)", "price": 180000, "category": "Miễn dịch"},
    {"code": "XN-MD-013", "name": "CEA (Dấu ấn ung thư tiêu hóa)", "price": 180000, "category": "Miễn dịch"},
    {"code": "XN-MD-014", "name": "PSA toàn phần (Tuyển tiền liệt)", "price": 180000, "category": "Miễn dịch"},
    {"code": "XN-MD-015", "name": "CA 125 (Buồng trứng)", "price": 180000, "category": "Miễn dịch"},
    {"code": "XN-MD-016", "name": "CA 15-3 (Vú)", "price": 180000, "category": "Miễn dịch"},
    {"code": "XN-MD-017", "name": "CA 19-9 (Tụy, dạ dày)", "price": 180000, "category": "Miễn dịch"},
    
    # ==========================================
    # ── VI SINH (MICROBIOLOGY) ──
    # ==========================================
    {"code": "XN-VS-001", "name": "Cấy máu", "price": 350000, "category": "Vi sinh"},
    {"code": "XN-VS-002", "name": "Cấy nước tiểu", "price": 250000, "category": "Vi sinh"},
    {"code": "XN-VS-003", "name": "Cấy đờm", "price": 250000, "category": "Vi sinh"},
    {"code": "XN-VS-004", "name": "Soi tươi dịch âm đạo", "price": 60000, "category": "Vi sinh"},
    {"code": "XN-VS-005", "name": "Nhuộm soi đờm tìm AFB (Lao)", "price": 60000, "category": "Vi sinh"},
    {"code": "XN-VS-006", "name": "Test nhanh Cúm A/B", "price": 180000, "category": "Vi sinh"},
    {"code": "XN-VS-007", "name": "Test nhanh Dengue NS1", "price": 180000, "category": "Vi sinh"},
    {"code": "XN-VS-008", "name": "PCR COVID-19", "price": 400000, "category": "Vi sinh"},
    {"code": "XN-VS-009", "name": "PCR lao (MTB)", "price": 500000, "category": "Vi sinh"},
    
    # ==========================================
    # ── CHẨN ĐOÁN HÌNH ẢNH (IMAGING) ──
    # ==========================================
    {"code": "CDHA-001", "name": "Siêu âm ổ bụng tổng quát", "price": 150000, "category": "CĐHA"},
    {"code": "CDHA-002", "name": "Siêu âm tuyến giáp", "price": 100000, "category": "CĐHA"},
    {"code": "CDHA-003", "name": "Siêu âm tuyến vú 2 bên", "price": 150000, "category": "CĐHA"},
    {"code": "CDHA-004", "name": "Siêu âm thai", "price": 150000, "category": "CĐHA"},
    {"code": "CDHA-005", "name": "Siêu âm Doppler tim", "price": 300000, "category": "CĐHA"},
    {"code": "CDHA-006", "name": "Siêu âm Doppler mạch máu chi dưới", "price": 250000, "category": "CĐHA"},
    {"code": "CDHA-007", "name": "Siêu âm phần mềm", "price": 100000, "category": "CĐHA"},
    
    {"code": "CDHA-XQ-001", "name": "X-Quang ngực thẳng", "price": 80000, "category": "CĐHA"},
    {"code": "CDHA-XQ-002", "name": "X-Quang bụng đứng không chuẩn bị", "price": 80000, "category": "CĐHA"},
    {"code": "CDHA-XQ-003", "name": "X-Quang cột sống cổ (thẳng/nghiêng)", "price": 120000, "category": "CĐHA"},
    {"code": "CDHA-XQ-004", "name": "X-Quang cột sống thắt lưng (thẳng/nghiêng)", "price": 120000, "category": "CĐHA"},
    {"code": "CDHA-XQ-005", "name": "X-Quang khung chậu thẳng", "price": 80000, "category": "CĐHA"},
    {"code": "CDHA-XQ-006", "name": "X-Quang khớp gối (thẳng/nghiêng) 1 bên", "price": 100000, "category": "CĐHA"},
    {"code": "CDHA-XQ-007", "name": "X-Quang sọ não thẳng/nghiêng", "price": 120000, "category": "CĐHA"},
    {"code": "CDHA-XQ-008", "name": "X-Quang xoang (Blondeau, Hirtz)", "price": 120000, "category": "CĐHA"},
    
    {"code": "CDHA-CT-001", "name": "Chụp CT sọ não không tiêm thuốc", "price": 800000, "category": "CĐHA"},
    {"code": "CDHA-CT-002", "name": "Chụp CT sọ não có tiêm thuốc", "price": 1200000, "category": "CĐHA"},
    {"code": "CDHA-CT-003", "name": "Chụp CT ngực không tiêm thuốc", "price": 900000, "category": "CĐHA"},
    {"code": "CDHA-CT-004", "name": "Chụp CT ngực có tiêm thuốc", "price": 1300000, "category": "CĐHA"},
    {"code": "CDHA-CT-005", "name": "Chụp CT ổ bụng có tiêm thuốc", "price": 1500000, "category": "CĐHA"},
    
    {"code": "CDHA-MRI-001", "name": "MRI sọ não không tiêm thuốc", "price": 1800000, "category": "CĐHA"},
    {"code": "CDHA-MRI-002", "name": "MRI sọ não có tiêm thuốc", "price": 2300000, "category": "CĐHA"},
    {"code": "CDHA-MRI-003", "name": "MRI cột sống thắt lưng", "price": 1800000, "category": "CĐHA"},
    {"code": "CDHA-MRI-004", "name": "MRI cột sống cổ", "price": 1800000, "category": "CĐHA"},
    {"code": "CDHA-MRI-005", "name": "MRI khớp gối", "price": 1800000, "category": "CĐHA"},

    # ==========================================
    # ── THĂM DÒ CHỨC NĂNG (FUNCTIONAL PROBING) ──
    # ==========================================
    {"code": "TDCN-001", "name": "Điện tâm đồ (ECG)", "price": 60000, "category": "Thăm dò chức năng"},
    {"code": "TDCN-002", "name": "Đo chức năng hô hấp (Hô hấp ký)", "price": 150000, "category": "Thăm dò chức năng"},
    {"code": "TDCN-003", "name": "Điện não đồ (EEG)", "price": 200000, "category": "Thăm dò chức năng"},
    {"code": "TDCN-004", "name": "Lưu huyết não", "price": 120000, "category": "Thăm dò chức năng"},
    {"code": "TDCN-005", "name": "Holter huyết áp 24h", "price": 400000, "category": "Thăm dò chức năng"},
    {"code": "TDCN-006", "name": "Holter điện tâm đồ 24h", "price": 500000, "category": "Thăm dò chức năng"},
    {"code": "TDCN-007", "name": "Nội soi dạ dày tá tràng không gây mê", "price": 400000, "category": "Thăm dò chức năng"},
    {"code": "TDCN-008", "name": "Nội soi dạ dày tá tràng có gây mê", "price": 900000, "category": "Thăm dò chức năng"},
    {"code": "TDCN-009", "name": "Nội soi đại tràng không gây mê", "price": 600000, "category": "Thăm dò chức năng"},
    {"code": "TDCN-010", "name": "Nội soi đại tràng có gây mê", "price": 1500000, "category": "Thăm dò chức năng"},
    {"code": "TDCN-011", "name": "Nội soi tai mũi họng cứng", "price": 120000, "category": "Thăm dò chức năng"},
    {"code": "TDCN-012", "name": "Nội soi tai mũi họng ống mềm", "price": 250000, "category": "Thăm dò chức năng"},
    {"code": "TDCN-013", "name": "Soi cổ tử cung", "price": 150000, "category": "Thăm dò chức năng"},
]

created = 0
for s in SERVICES:
    obj, is_new = ServiceList.objects.update_or_create(
        code=s["code"],
        defaults={
            "name": s["name"],
            "price": s["price"],
            "category": s["category"],
        }
    )
    if is_new:
        created += 1

print(f"[Seed CLS] Done — {created} created, {len(SERVICES) - created} updated. Total: {len(SERVICES)}")
