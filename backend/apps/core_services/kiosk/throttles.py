"""
Kiosk Rate Throttle — Layer 3 (Rate Limiting)

Giới hạn số request từ cùng 1 IP (máy Kiosk) để tránh spam.
Mặc định: 10 request/phút.
"""

from rest_framework.throttling import SimpleRateThrottle


class KioskRateThrottle(SimpleRateThrottle):
    """
    Rate limit cho endpoint Kiosk.
    
    Scope 'kiosk' được cấu hình trong settings.py:
        REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {'kiosk': '10/min'}
    
    Sử dụng IP làm key, vì Kiosk là thiết bị public (không có user login).
    """
    scope = 'kiosk'

    def get_cache_key(self, request, view):
        """Dùng IP address làm key phân biệt."""
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }
