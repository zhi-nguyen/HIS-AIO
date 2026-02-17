"""
Django models for PgVector storage.

Stores embeddings and metadata for clinical records and ICD-10 codes.
"""

from django.db import models
from pgvector.django import VectorField
from apps.core_services.core.models import UUIDModel


class VectorDocument(UUIDModel):
    """
    Base model for storing document embeddings with vector search capability.
    
    Supports both clinical records and ICD-10 codes with separate collections.
    """
    
    class CollectionType(models.TextChoices):
        CLINICAL_RECORDS = 'clinical_records', 'Clinical Records'
        ICD10_CODES = 'icd10_codes', 'ICD-10 Codes'
        DRUGS = 'drugs', 'Drugs & Interactions'
        MEDICAL_PROTOCOLS = 'medical_protocols', 'Medical Protocols'
        HOSPITAL_PROCESS = 'hospital_process', 'Hospital Process Q&A'
        DEPARTMENTS = 'departments', 'Departments'
    
    # Collection info
    collection = models.CharField(
        max_length=50,
        choices=CollectionType.choices,
        db_index=True,
        help_text="Collection type (clinical_records or icd10_codes)"
    )
    
    # Document info
    document_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Original document ID (UUID or code)"
    )
    
    document_text = models.TextField(
        help_text="Full text content of the document"
    )
    
    # Vector embedding
    embedding = VectorField(
        dimensions=768,  # Configurable based on embedding model
        help_text="Vector embedding of the document"
    )
    
    # Metadata stored as JSON
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata (patient_id, visit_code, diagnosis, etc.)"
    )
    
    class Meta:
        verbose_name = "Vector Document"
        verbose_name_plural = "Vector Documents"
        indexes = [
            models.Index(fields=['collection', 'document_id']),
            models.Index(fields=['collection', 'created_at']),
        ]
        # Prevent duplicate documents in same collection
        unique_together = [['collection', 'document_id']]
    
    def __str__(self):
        return f"{self.collection}: {self.document_id}"
