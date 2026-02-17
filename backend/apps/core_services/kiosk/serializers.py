"""
Kiosk Serializers — Validate đầu vào cho API Kiosk tự phục vụ.
"""

import re
from rest_framework import serializers


class KioskIdentifySerializer(serializers.Serializer):
    """
    Validate dữ liệu quét QR từ CCCD/BHYT.
    
    scan_data chấp nhận:
      - CCCD: 12 ký tự số
      - Mã BHYT mới (số BHYT): 10 ký tự số
      - Mã BHYT cũ (đầy đủ): 15 ký tự (2 chữ + 13 số)
    """
    scan_data = serializers.CharField(
        min_length=10,
        max_length=15,
        help_text="Dữ liệu quét từ QR CCCD (12 số) hoặc mã BHYT (10/15 ký tự)"
    )

    def validate_scan_data(self, value):
        """Kiểm tra format CCCD hoặc BHYT."""
        v = value.strip()
        
        # CCCD: 12 ký tự số
        if re.match(r'^\d{12}$', v):
            return v
        
        # Mã BHYT mới: 10 ký tự số
        if re.match(r'^\d{10}$', v):
            return v
        
        # Mã BHYT cũ: 2 chữ + 13 số = 15 ký tự
        if re.match(r'^[A-Za-z]{2}\d{13}$', v):
            return v.upper()
        
        raise serializers.ValidationError(
            "Dữ liệu quét không hợp lệ. "
            "Chấp nhận: CCCD (12 số), mã BHYT mới (10 số), "
            "hoặc mã BHYT cũ (15 ký tự, VD: TE1790000000123)."
        )


class KioskRegisterSerializer(serializers.Serializer):
    """
    Validate đăng ký lượt khám từ Kiosk.
    
    patient_id: UUID bệnh nhân (từ bước identify)
    chief_complaint: Lý do khám (tối thiểu 3 ký tự)
    """
    patient_id = serializers.UUIDField(
        help_text="UUID bệnh nhân từ bước identify"
    )
    chief_complaint = serializers.CharField(
        min_length=3,
        max_length=1000,
        help_text="Lý do khám / triệu chứng (tối thiểu 3 ký tự)"
    )
