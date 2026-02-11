"""
Tests cho Insurance Mock API.

Test cases:
  1. Tra cứu bằng CCCD (12 số) → success
  2. Tra cứu bằng mã BHYT mới (10 số) → success
  3. Tra cứu bằng mã BHYT cũ (15 ký tự) → success
  4. Tra cứu thẻ hết hạn → expired
  5. Tra cứu không tồn tại → not_found
  6. Input sai format → HTTP 400
  7. Thiếu field query → HTTP 400
  8. Body không phải JSON → HTTP 400
"""

import json
from django.test import TestCase, Client


class InsuranceLookupAPITest(TestCase):
    """Kiểm tra endpoint POST /api/v1/insurance/lookup/"""

    def setUp(self):
        self.client = Client()
        self.url = '/api/v1/insurance/lookup/'

    # ------------------------------------------------------------------
    # 1. Tra cứu bằng CCCD (12 số)
    # ------------------------------------------------------------------
    def test_lookup_by_cccd_success(self):
        """CCCD 12 số hợp lệ → trả về thông tin BHYT."""
        response = self.client.post(
            self.url,
            data=json.dumps({"query": "092200012345"}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIsNotNone(data["data"])
        self.assertEqual(data["data"]["patient_name"], "NGUYEN VAN AN")
        self.assertEqual(data["data"]["benefit_code"], "TE")
        self.assertEqual(data["data"]["benefit_rate"], 100)
        self.assertIn("check_time", data["data"])

    # ------------------------------------------------------------------
    # 2. Tra cứu bằng mã BHYT mới (10 số)
    # ------------------------------------------------------------------
    def test_lookup_by_short_code_success(self):
        """Mã BHYT mới 10 số → trả về thông tin BHYT."""
        response = self.client.post(
            self.url,
            data=json.dumps({"query": "0000000456"}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["patient_name"], "TRAN THI BICH")
        self.assertEqual(data["data"]["benefit_code"], "DN")
        self.assertEqual(data["data"]["benefit_rate"], 80)

    # ------------------------------------------------------------------
    # 3. Tra cứu bằng mã BHYT cũ (15 ký tự)
    # ------------------------------------------------------------------
    def test_lookup_by_full_code_success(self):
        """Mã BHYT đầy đủ 15 ký tự → trả về thông tin BHYT."""
        response = self.client.post(
            self.url,
            data=json.dumps({"query": "HT7920000001234"}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["patient_name"], "PHAM VAN DUNG")
        self.assertEqual(data["data"]["benefit_code"], "HT")
        self.assertEqual(data["data"]["benefit_rate"], 95)
        self.assertTrue(data["data"]["is_5_years_consecutive"])

    def test_lookup_by_full_code_case_insensitive(self):
        """Mã BHYT full code không phân biệt hoa thường."""
        response = self.client.post(
            self.url,
            data=json.dumps({"query": "ht7920000001234"}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["patient_name"], "PHAM VAN DUNG")

    # ------------------------------------------------------------------
    # 4. Tra cứu thẻ hết hạn
    # ------------------------------------------------------------------
    def test_lookup_expired_card(self):
        """Thẻ BHYT đã hết hạn → status 'expired'."""
        response = self.client.post(
            self.url,
            data=json.dumps({"query": "079088008888"}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "expired")
        self.assertIsNotNone(data["data"])
        self.assertEqual(data["data"]["patient_name"], "DO THI HANH")

    # ------------------------------------------------------------------
    # 5. Tra cứu không tồn tại
    # ------------------------------------------------------------------
    def test_lookup_not_found_cccd(self):
        """CCCD không tồn tại → status 'not_found'."""
        response = self.client.post(
            self.url,
            data=json.dumps({"query": "999999999999"}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "not_found")
        self.assertIsNone(data["data"])

    def test_lookup_not_found_short(self):
        """Mã BHYT ngắn không tồn tại → not_found."""
        response = self.client.post(
            self.url,
            data=json.dumps({"query": "9999999999"}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "not_found")

    def test_lookup_not_found_full(self):
        """Mã BHYT full không tồn tại → not_found."""
        response = self.client.post(
            self.url,
            data=json.dumps({"query": "XX9999999999999"}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "not_found")

    # ------------------------------------------------------------------
    # 6. Input sai format
    # ------------------------------------------------------------------
    def test_invalid_format_too_short(self):
        """Chuỗi quá ngắn → HTTP 400."""
        response = self.client.post(
            self.url,
            data=json.dumps({"query": "12345"}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["code"], "INVALID_FORMAT")

    def test_invalid_format_letters_in_cccd(self):
        """CCCD chứa chữ → HTTP 400."""
        response = self.client.post(
            self.url,
            data=json.dumps({"query": "09220001ABCD"}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_format_too_long(self):
        """Chuỗi quá dài → HTTP 400."""
        response = self.client.post(
            self.url,
            data=json.dumps({"query": "1234567890123456"}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    # ------------------------------------------------------------------
    # 7. Thiếu field query
    # ------------------------------------------------------------------
    def test_missing_query_field(self):
        """Thiếu field query → HTTP 400."""
        response = self.client.post(
            self.url,
            data=json.dumps({"something_else": "abc"}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["code"], "MISSING_QUERY")

    def test_empty_query_field(self):
        """Query rỗng → HTTP 400."""
        response = self.client.post(
            self.url,
            data=json.dumps({"query": ""}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    # ------------------------------------------------------------------
    # 8. Body không phải JSON
    # ------------------------------------------------------------------
    def test_invalid_json_body(self):
        """Body không phải JSON → HTTP 400."""
        response = self.client.post(
            self.url,
            data="this is not json",
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["code"], "INVALID_JSON")

    # ------------------------------------------------------------------
    # 9. Response cần có đầy đủ các trường theo spec
    # ------------------------------------------------------------------
    def test_response_has_all_required_fields(self):
        """Kiểm tra response chứa tất cả trường theo yêu cầu."""
        response = self.client.post(
            self.url,
            data=json.dumps({"query": "092200012345"}),
            content_type='application/json',
        )
        data = response.json()
        required_fields = [
            "patient_name", "insurance_code", "dob", "gender", "address",
            "card_issue_date", "card_expire_date", "benefit_rate",
            "benefit_code", "registered_hospital_code",
            "registered_hospital_name", "is_5_years_consecutive",
            "check_time",
        ]
        for field in required_fields:
            self.assertIn(field, data["data"], f"Missing field: {field}")

    # ------------------------------------------------------------------
    # 10. Chỉ chấp nhận POST
    # ------------------------------------------------------------------
    def test_get_method_not_allowed(self):
        """GET method → HTTP 405."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
