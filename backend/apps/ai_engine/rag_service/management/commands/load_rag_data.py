"""
Management command to load data into RAG vector database.

Usage:
    python manage.py load_rag_data --clinical-records --icd10-codes
    python manage.py load_rag_data --clinical-records --batch-size 50
    python manage.py load_rag_data --icd10-codes
"""

from django.core.management.base import BaseCommand
import asyncio
import logging

from apps.ai_engine.rag_service.data_loader import (
    load_clinical_records_to_vector_db,
    load_icd10_codes_to_vector_db,
    load_departments_to_vector_db
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Load clinical records and ICD-10 codes into RAG vector database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clinical-records',
            action='store_true',
            help='Load clinical records into vector database',
        )
        parser.add_argument(
            '--icd10-codes',
            action='store_true',
            help='Load ICD-10 codes into vector database',
        )
        parser.add_argument(
            '--departments',
            action='store_true',
            help='Load departments into vector database',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of records to process per batch (default: 100)',
        )
        parser.add_argument(
            '--provider',
            type=str,
            default=None,
            help='Embedding provider override (google, openai, sentence-transformers)',
        )
    
    def handle(self, *args, **options):
        load_clinical = options['clinical_records']
        load_icd10 = options['icd10_codes']
        load_departments = options['departments']
        batch_size = options['batch_size']
        provider = options['provider']
        
        # If no specific option, load all
        if not load_clinical and not load_icd10 and not load_departments:
            load_clinical = True
            load_icd10 = True
            load_departments = True
        
        self.stdout.write(self.style.SUCCESS('Starting RAG data loading...'))
        
        # Run async loading
        asyncio.run(self._async_load(
            load_clinical=load_clinical,
            load_icd10=load_icd10,
            load_departments=load_departments,
            batch_size=batch_size,
            provider=provider
        ))
    
    async def _async_load(self, load_clinical, load_icd10, load_departments, batch_size, provider):
        """Async loading of data."""
        from apps.ai_engine.rag_service.embeddings import EmbeddingService
        from apps.ai_engine.rag_service.vector_service import VectorService
        
        # Initialize services with optional provider override
        embedding_service = None
        if provider:
            self.stdout.write(f'Using embedding provider: {provider}')
            embedding_service = EmbeddingService(provider=provider)
        
        vector_service = VectorService()
        
        # Load clinical records
        if load_clinical:
            self.stdout.write(self.style.WARNING('Loading clinical records...'))
            try:
                count = await load_clinical_records_to_vector_db(
                    batch_size=batch_size,
                    vector_service=vector_service,
                    embedding_service=embedding_service
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Successfully loaded {count} clinical records')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error loading clinical records: {e}')
                )
        
        # Load ICD-10 codes
        if load_icd10:
            self.stdout.write(self.style.WARNING('Loading ICD-10 codes...'))
            try:
                count = await load_icd10_codes_to_vector_db(
                    batch_size=batch_size,
                    vector_service=vector_service,
                    embedding_service=embedding_service
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Successfully loaded {count} ICD-10 codes')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error loading ICD-10 codes: {e}')
                )
        
        # Load departments
        if load_departments:
            self.stdout.write(self.style.WARNING('Loading departments...'))
            try:
                count = await load_departments_to_vector_db(
                    vector_service=vector_service,
                    embedding_service=embedding_service
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Successfully loaded {count} departments')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error loading departments: {e}')
                )
        
        self.stdout.write(self.style.SUCCESS('\n✓ RAG data loading completed!'))
