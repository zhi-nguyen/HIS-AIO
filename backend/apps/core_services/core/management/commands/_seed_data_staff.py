"""
Dữ liệu seed: Staff + User accounts
Mỗi khoa lâm sàng ít nhất 1 bác sĩ riêng biệt + các role khác.
"""

# Password mặc định cho tất cả tài khoản test
DEFAULT_PASSWORD = "Test@123"

# (email, first_name, last_name, role, staff_code, department_code, position)
STAFF_DATA = [
    # === ADMIN ===
    ("admin@bv.local", "Quản Trị", "Hệ Thống", "ADMIN", "NV-ADMIN", None, None),

    # === RECEPTIONIST ===
    ("receptionist@bv.local", "Thị Hoa", "Nguyễn", "RECEPTIONIST", "NV-TD01", None, None),

    # === NURSE ===
    ("nurse@bv.local", "Thị Lan", "Trần", "NURSE", "NV-DD01", "NOI_TQ", "NURSING_STAFF"),

    # === LAB TECHNICIAN ===
    ("lab@bv.local", "Văn Minh", "Phạm", "LAB_TECHNICIAN", "NV-XN01", "XN", "MEDICAL_STAFF"),

    # === PHARMACIST ===
    ("pharmacist@bv.local", "Thị Mai", "Lê", "PHARMACIST", "NV-DS01", "DUOC", "MEDICAL_STAFF"),

    # === BÁC SĨ MỖI KHOA ===
    ("bs.capcuu@bv.local", "Văn An", "Nguyễn", "DOCTOR", "BS-CC01", "CC", "HEAD"),
    ("bs.noitq@bv.local", "Minh Tuấn", "Trần", "DOCTOR", "BS-NTQ01", "NOI_TQ", "HEAD"),
    ("bs.noitm@bv.local", "Quốc Hùng", "Lê", "DOCTOR", "BS-NTM01", "NOI_TM", "HEAD"),
    ("bs.noith@bv.local", "Thị Hằng", "Phạm", "DOCTOR", "BS-NTH01", "NOI_TH", "HEAD"),
    ("bs.noihh@bv.local", "Đức Thịnh", "Võ", "DOCTOR", "BS-NHH01", "NOI_HH", "HEAD"),
    ("bs.noitk@bv.local", "Thanh Sơn", "Đặng", "DOCTOR", "BS-NTK01", "NOI_TK", "HEAD"),
    ("bs.noint@bv.local", "Thị Nga", "Hoàng", "DOCTOR", "BS-NNT01", "NOI_NT", "HEAD"),
    ("bs.ngoaitq@bv.local", "Văn Đức", "Bùi", "DOCTOR", "BS-NGT01", "NGOAI_TQ", "HEAD"),
    ("bs.ngoaict@bv.local", "Trung Kiên", "Đỗ", "DOCTOR", "BS-NGC01", "NGOAI_CT", "HEAD"),
    ("bs.ngoaitk@bv.local", "Hữu Phúc", "Ngô", "DOCTOR", "BS-NGTK01", "NGOAI_TK", "HEAD"),
    ("bs.san@bv.local", "Thị Thanh", "Dương", "DOCTOR", "BS-SAN01", "SAN", "HEAD"),
    ("bs.nhi@bv.local", "Minh Châu", "Lý", "DOCTOR", "BS-NHI01", "NHI", "HEAD"),
    ("bs.tmh@bv.local", "Quang Vinh", "Trịnh", "DOCTOR", "BS-TMH01", "TMH", "HEAD"),
    ("bs.rhm@bv.local", "Hải Đăng", "Vũ", "DOCTOR", "BS-RHM01", "RHM", "HEAD"),
    ("bs.mat@bv.local", "Thị Linh", "Mai", "DOCTOR", "BS-MAT01", "MAT", "HEAD"),
    ("bs.dalieu@bv.local", "Hoàng Anh", "Phan", "DOCTOR", "BS-DL01", "DALIEU", "HEAD"),
    ("bs.ub@bv.local", "Quốc Bảo", "Đinh", "DOCTOR", "BS-UB01", "UB", "HEAD"),
    ("bs.tn@bv.local", "Văn Lâm", "Tạ", "DOCTOR", "BS-TN01", "TN", "HEAD"),
    ("bs.tt@bv.local", "Minh Khoa", "Lương", "DOCTOR", "BS-TT01", "TT", "HEAD"),
    ("bs.phcn@bv.local", "Thị Huyền", "Cao", "DOCTOR", "BS-PHCN01", "PHCN", "HEAD"),
    ("bs.yhct@bv.local", "Đình Trung", "Hà", "DOCTOR", "BS-YHCT01", "YHCT", "HEAD"),
    ("bs.cdha@bv.local", "Văn Tâm", "Nghiêm", "DOCTOR", "BS-CDHA01", "CDHA", "HEAD"),
    ("bs.gmhs@bv.local", "Quốc Toàn", "Tô", "DOCTOR", "BS-GMHS01", "GMHS", "HEAD"),
]
