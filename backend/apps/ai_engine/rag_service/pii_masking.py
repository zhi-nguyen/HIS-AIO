"""
PII Masking Utilities for Healthcare RAG Service

Provides functions to mask personally identifiable information (PII)
in logs while preserving data utility for LLM context.
"""

import hashlib
import re
from typing import Any, Dict


def mask_patient_id(patient_id: str) -> str:
    """
    Hash patient ID for secure logging.
    
    Args:
        patient_id: The patient ID to mask
        
    Returns:
        Hashed patient ID (first 8 characters of SHA-256)
    """
    if not patient_id:
        return "UNKNOWN"
    
    hash_obj = hashlib.sha256(str(patient_id).encode())
    return f"P_{hash_obj.hexdigest()[:8]}"


def mask_id_card(id_card: str) -> str:
    """
    Mask ID card number (CCCD/CMND).
    
    Args:
        id_card: ID card number
        
    Returns:
        Masked ID card (e.g., "***********234")
    """
    if not id_card or len(id_card) < 3:
        return "***"
    
    return "*" * (len(id_card) - 3) + id_card[-3:]


def mask_phone_number(phone: str) -> str:
    """
    Mask phone number.
    
    Args:
        phone: Phone number
        
    Returns:
        Masked phone (e.g., "***-***-1234")
    """
    if not phone or len(phone) < 4:
        return "***"
    
    return "***-***-" + phone[-4:]


def mask_insurance_number(insurance_no: str) -> str:
    """
    Mask insurance number.
    
    Args:
        insurance_no: Insurance number
        
    Returns:
        Masked insurance number
    """
    if not insurance_no or len(insurance_no) < 4:
        return "***"
    
    return insurance_no[:2] + "*" * (len(insurance_no) - 4) + insurance_no[-2:]


def mask_sensitive_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask sensitive fields in a dictionary for logging.
    
    Args:
        data: Dictionary potentially containing PII
        
    Returns:
        Dictionary with PII fields masked
    """
    masked_data = data.copy()
    
    # List of sensitive field names
    sensitive_fields = {
        'id_card': mask_id_card,
        'insurance_number': mask_insurance_number,
        'contact_number': mask_phone_number,
        'phone': mask_phone_number,
        'patient_id': mask_patient_id,
    }
    
    for field, masker in sensitive_fields.items():
        if field in masked_data and masked_data[field]:
            masked_data[field] = masker(str(masked_data[field]))
    
    return masked_data


def sanitize_log_message(message: str) -> str:
    """
    Remove potential PII from log messages using regex patterns.
    
    Args:
        message: Log message to sanitize
        
    Returns:
        Sanitized message with PII replaced
    """
    # Mask potential Vietnamese ID cards (9 or 12 digits)
    message = re.sub(r'\b\d{9}\b', '***ID***', message)
    message = re.sub(r'\b\d{12}\b', '***ID***', message)
    
    # Mask potential phone numbers (format: 0xxxxxxxxx or +84xxxxxxxxx)
    message = re.sub(r'\b(\+84|0)\d{9}\b', '***PHONE***', message)
    
    # Mask potential insurance numbers (pattern: XXnnnnnnnnnnn)
    message = re.sub(r'\b[A-Z]{2}\d{11,13}\b', '***INSURANCE***', message)
    
    return message
