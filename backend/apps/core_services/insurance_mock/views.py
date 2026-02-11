"""
Insurance Mock API Views

Endpoint tra cứu thông tin Bảo Hiểm Y Tế (BHYT) giả lập.
Hỗ trợ 3 loại đầu vào:
  - CCCD: 12 ký tự số
  - Mã BHYT mới (số BHYT): 10 ký tự số
  - Mã BHYT cũ (đầy đủ): 15 ký tự (2 chữ + 2 số tỉnh + 1 số phụ + 10 số BHYT)
"""

import json
import re
import copy
import logging
from datetime import datetime, timezone

from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .mock_data import LOOKUP_BY_CCCD, LOOKUP_BY_SHORT_CODE, LOOKUP_BY_FULL_CODE

logger = logging.getLogger(__name__)


# ==============================================================================
# REGEX PATTERNS cho phân loại đầu vào
# ==============================================================================

# CCCD: chính xác 12 ký tự số
PATTERN_CCCD = re.compile(r'^\d{12}$')

# Mã BHYT mới (số BHYT): chính xác 10 ký tự số
PATTERN_INSURANCE_SHORT = re.compile(r'^\d{10}$')

# Mã BHYT cũ (đầy đủ): 2 chữ cái + 13 ký tự (số + có thể chữ) = 15 ký tự
# Format: [A-Z]{2} + [0-9]{2} (mã tỉnh) + [0-9]{1} (mã đối tượng phụ) + [0-9]{10} (số BHYT)
PATTERN_INSURANCE_FULL = re.compile(r'^[A-Za-z]{2}\d{13}$')


def _classify_query(query: str) -> str:
    """
    Phân loại chuỗi tra cứu.
    Returns: 'cccd' | 'insurance_short' | 'insurance_full' | 'invalid'
    """
    q = query.strip()
    if PATTERN_CCCD.match(q):
        return 'cccd'
    if PATTERN_INSURANCE_SHORT.match(q):
        return 'insurance_short'
    if PATTERN_INSURANCE_FULL.match(q):
        return 'insurance_full'
    return 'invalid'


def _check_expiry(data: dict) -> str:
    """
    Kiểm tra thẻ BHYT còn hạn hay không.
    Returns: 'success' | 'expired'
    """
    expire_str = data.get("card_expire_date", "")
    if not expire_str:
        return "success"
    try:
        expire_date = datetime.strptime(expire_str, "%Y-%m-%d").date()
        if expire_date < datetime.now().date():
            return "expired"
    except ValueError:
        pass
    return "success"


# ==============================================================================
# API VIEW
# ==============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def lookup_insurance(request: HttpRequest) -> JsonResponse:
    """
    Tra cứu thông tin BHYT theo CCCD hoặc mã BHYT.

    Request Body:
        {
            "query": "092200012345"  // CCCD 12 số
                                     // hoặc "0000000123" (mã BHYT mới 10 số)
                                     // hoặc "TE1790000000123" (mã BHYT cũ 15 ký tự)
        }

    Response (success):
        {
            "status": "success",
            "data": { ... thông tin BHYT ... }
        }

    Response (expired):
        {
            "status": "expired",
            "data": { ... thông tin BHYT ... }
        }

    Response (not_found):
        {
            "status": "not_found",
            "data": null
        }
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "Invalid JSON body", "code": "INVALID_JSON"},
            status=400,
        )

    query = body.get("query", "").strip()
    if not query:
        return JsonResponse(
            {"error": "Trường 'query' là bắt buộc", "code": "MISSING_QUERY"},
            status=400,
        )

    # --- Phân loại đầu vào ---
    query_type = _classify_query(query)

    if query_type == 'invalid':
        return JsonResponse(
            {
                "error": (
                    "Giá trị query không hợp lệ. "
                    "Chấp nhận: CCCD (12 số), mã BHYT mới (10 số), "
                    "hoặc mã BHYT cũ (15 ký tự, ví dụ TE1790000000123)."
                ),
                "code": "INVALID_FORMAT",
            },
            status=400,
        )

    # --- Tra cứu ---
    record = None
    if query_type == 'cccd':
        record = LOOKUP_BY_CCCD.get(query)
    elif query_type == 'insurance_short':
        record = LOOKUP_BY_SHORT_CODE.get(query)
    elif query_type == 'insurance_full':
        record = LOOKUP_BY_FULL_CODE.get(query.upper())

    if record is None:
        return JsonResponse(
            {
                "status": "not_found",
                "data": None,
            },
            json_dumps_params={"ensure_ascii": False},
        )

    # --- Deep copy để không ảnh hưởng dữ liệu gốc ---
    result = copy.deepcopy(record)

    # --- Kiểm tra hết hạn ---
    status = _check_expiry(result)

    # --- Thêm check_time ---
    result["check_time"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return JsonResponse(
        {
            "status": status,
            "data": result,
        },
        json_dumps_params={"ensure_ascii": False},
    )
