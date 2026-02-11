"""
Dữ liệu giả lập Bảo Hiểm Y Tế (BHYT) cho Insurance Mock API.

Cấu trúc mã BHYT 15 ký tự:
  - 2 ký tự: Mã mức hưởng / đối tượng (TE, DN, GD, HN, HT, HS, SV, CC, CK...)
  - 2 ký tự: Mã tỉnh/thành nơi sinh sống (79 = TP.HCM, 92 = Cần Thơ, 01 = Hà Nội...)
  - 1 ký tự: Mã đối tượng phụ (0-9)
  - 10 ký tự: Số BHYT (số)

Ví dụ: TE1790000000123
  - TE = Trẻ em
  - 17 = mã nơi sinh sống  
  - 9 = mã đối tượng phụ
  - 0000000123 = số BHYT
"""

from datetime import datetime

# ==============================================================================
# MOCK INSURANCE RECORDS
# ==============================================================================

MOCK_RECORDS = [
    # --- 1. Trẻ em (TE) - Mức hưởng 100% ---
    {
        "cccd": "092200012345",
        "insurance_code": "TE1790000000123",
        "insurance_short": "0000000123",
        "data": {
            "patient_name": "NGUYEN VAN AN",
            "insurance_code": "TE1790000000123",
            "dob": "2021-03-15",
            "gender": "male",
            "address": "Phường An Khánh, Quận Ninh Kiều, TP Cần Thơ",
            "card_issue_date": "2021-03-15",
            "card_expire_date": "2027-03-15",
            "benefit_rate": 100,
            "benefit_code": "TE",
            "registered_hospital_code": "92001",
            "registered_hospital_name": "Bệnh viện Nhi Đồng Cần Thơ",
            "is_5_years_consecutive": False,
        }
    },
    # --- 2. Doanh nghiệp (DN) - Mức hưởng 80% ---
    {
        "cccd": "079085001234",
        "insurance_code": "DN7910000000456",
        "insurance_short": "0000000456",
        "data": {
            "patient_name": "TRAN THI BICH",
            "insurance_code": "DN7910000000456",
            "dob": "1985-07-20",
            "gender": "female",
            "address": "Phường Bến Nghé, Quận 1, TP Hồ Chí Minh",
            "card_issue_date": "2022-01-01",
            "card_expire_date": "2027-12-31",
            "benefit_rate": 80,
            "benefit_code": "DN",
            "registered_hospital_code": "79002",
            "registered_hospital_name": "Bệnh viện Chợ Rẫy",
            "is_5_years_consecutive": True,
        }
    },
    # --- 3. Gia đình (GD) - Mức hưởng 80% ---
    {
        "cccd": "001090005678",
        "insurance_code": "GD0120000000789",
        "insurance_short": "0000000789",
        "data": {
            "patient_name": "LE VAN CUONG",
            "insurance_code": "GD0120000000789",
            "dob": "1990-11-03",
            "gender": "male",
            "address": "Phường Hoàn Kiếm, Quận Hoàn Kiếm, TP Hà Nội",
            "card_issue_date": "2023-06-01",
            "card_expire_date": "2027-05-31",
            "benefit_rate": 80,
            "benefit_code": "GD",
            "registered_hospital_code": "01003",
            "registered_hospital_name": "Bệnh viện Bạch Mai",
            "is_5_years_consecutive": False,
        }
    },
    # --- 4. Hưu trí (HT) - Mức hưởng 95% ---
    {
        "cccd": "079055004321",
        "insurance_code": "HT7920000001234",
        "insurance_short": "0000001234",
        "data": {
            "patient_name": "PHAM VAN DUNG",
            "insurance_code": "HT7920000001234",
            "dob": "1955-02-10",
            "gender": "male",
            "address": "Phường Thạnh Mỹ Lợi, TP Thủ Đức, TP Hồ Chí Minh",
            "card_issue_date": "2015-03-01",
            "card_expire_date": "2027-12-31",
            "benefit_rate": 95,
            "benefit_code": "HT",
            "registered_hospital_code": "79004",
            "registered_hospital_name": "Bệnh viện Thống Nhất",
            "is_5_years_consecutive": True,
        }
    },
    # --- 5. Hộ nghèo (HN) - Mức hưởng 100% ---
    {
        "cccd": "038075009876",
        "insurance_code": "HN3810000005678",
        "insurance_short": "0000005678",
        "data": {
            "patient_name": "HOANG THI EM",
            "insurance_code": "HN3810000005678",
            "dob": "1975-08-25",
            "gender": "female",
            "address": "Xã Đại Đồng, Huyện Văn Lâm, Tỉnh Hưng Yên",
            "card_issue_date": "2024-01-01",
            "card_expire_date": "2027-12-31",
            "benefit_rate": 100,
            "benefit_code": "HN",
            "registered_hospital_code": "38001",
            "registered_hospital_name": "Bệnh viện Đa khoa Hưng Yên",
            "is_5_years_consecutive": True,
        }
    },
    # --- 6. Học sinh (HS) - Mức hưởng 80% ---
    {
        "cccd": "092210006543",
        "insurance_code": "HS9210000009012",
        "insurance_short": "0000009012",
        "data": {
            "patient_name": "VO MINH PHUC",
            "insurance_code": "HS9210000009012",
            "dob": "2010-09-01",
            "gender": "male",
            "address": "Phường Xuân Khánh, Quận Ninh Kiều, TP Cần Thơ",
            "card_issue_date": "2024-09-01",
            "card_expire_date": "2025-08-31",
            "benefit_rate": 80,
            "benefit_code": "HS",
            "registered_hospital_code": "92002",
            "registered_hospital_name": "Bệnh viện Đa khoa TP Cần Thơ",
            "is_5_years_consecutive": False,
        }
    },
    # --- 7. Cựu chiến binh (CC) - Mức hưởng 100% ---
    {
        "cccd": "048045007777",
        "insurance_code": "CC4810000003456",
        "insurance_short": "0000003456",
        "data": {
            "patient_name": "NGUYEN THANH GIANG",
            "insurance_code": "CC4810000003456",
            "dob": "1945-04-30",
            "gender": "male",
            "address": "Phường 1, TP Đà Lạt, Tỉnh Lâm Đồng",
            "card_issue_date": "2010-01-01",
            "card_expire_date": "2030-12-31",
            "benefit_rate": 100,
            "benefit_code": "CC",
            "registered_hospital_code": "48001",
            "registered_hospital_name": "Bệnh viện Đa khoa Lâm Đồng",
            "is_5_years_consecutive": True,
        }
    },
    # --- 8. Thẻ HẾT HẠN (DN) - để test status expired ---
    {
        "cccd": "079088008888",
        "insurance_code": "DN7920000007890",
        "insurance_short": "0000007890",
        "data": {
            "patient_name": "DO THI HANH",
            "insurance_code": "DN7920000007890",
            "dob": "1988-12-01",
            "gender": "female",
            "address": "Phường Tân Định, Quận 1, TP Hồ Chí Minh",
            "card_issue_date": "2023-01-01",
            "card_expire_date": "2025-12-31",
            "benefit_rate": 80,
            "benefit_code": "DN",
            "registered_hospital_code": "79005",
            "registered_hospital_name": "Bệnh viện Nhân Dân 115",
            "is_5_years_consecutive": False,
        }
    },
    # --- 9. Sinh viên (SV) - Mức hưởng 80% ---
    {
        "cccd": "092200019999",
        "insurance_code": "SV9220000002345",
        "insurance_short": "0000002345",
        "data": {
            "patient_name": "HUYNH QUOC KHANH",
            "insurance_code": "SV9220000002345",
            "dob": "2003-05-15",
            "gender": "male",
            "address": "Phường An Hòa, Quận Ninh Kiều, TP Cần Thơ",
            "card_issue_date": "2024-09-01",
            "card_expire_date": "2027-08-31",
            "benefit_rate": 80,
            "benefit_code": "SV",
            "registered_hospital_code": "92003",
            "registered_hospital_name": "Trung tâm Y tế Quận Ninh Kiều",
            "is_5_years_consecutive": False,
        }
    },
    # --- 10. Thân nhân người có công (CK) - Mức hưởng 80% ---
    {
        "cccd": "036070001111",
        "insurance_code": "CK3610000006789",
        "insurance_short": "0000006789",
        "data": {
            "patient_name": "BUI THI LOAN",
            "insurance_code": "CK3610000006789",
            "dob": "1970-01-20",
            "gender": "female",
            "address": "Phường Đông Thành, TP Ninh Bình, Tỉnh Ninh Bình",
            "card_issue_date": "2020-01-01",
            "card_expire_date": "2027-12-31",
            "benefit_rate": 80,
            "benefit_code": "CK",
            "registered_hospital_code": "36001",
            "registered_hospital_name": "Bệnh viện Đa khoa Ninh Bình",
            "is_5_years_consecutive": True,
        }
    },
]


# ==============================================================================
# LOOKUP DICTIONARIES (Tạo sẵn để tra cứu O(1))
# ==============================================================================

def _build_lookups():
    """Xây dựng 3 dict tra cứu từ danh sách mock records."""
    by_cccd = {}
    by_short = {}
    by_full = {}
    for record in MOCK_RECORDS:
        by_cccd[record["cccd"]] = record["data"]
        by_short[record["insurance_short"]] = record["data"]
        by_full[record["insurance_code"].upper()] = record["data"]
    return by_cccd, by_short, by_full


LOOKUP_BY_CCCD, LOOKUP_BY_SHORT_CODE, LOOKUP_BY_FULL_CODE = _build_lookups()
