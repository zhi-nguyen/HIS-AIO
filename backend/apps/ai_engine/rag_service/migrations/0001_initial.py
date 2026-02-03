
import pgvector.django.vector
from pgvector.django import VectorExtension
import uuid6
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        VectorExtension(),
        migrations.CreateModel(
            name='VectorDocument',
            fields=[
                ('id', models.UUIDField(default=uuid6.uuid7, editable=False, primary_key=True, serialize=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('version', models.IntegerField(default=1)),
                ('collection', models.CharField(choices=[('clinical_records', 'Clinical Records'), ('icd10_codes', 'ICD-10 Codes'), ('drugs', 'Drugs & Interactions'), ('medical_protocols', 'Medical Protocols'), ('hospital_process', 'Hospital Process Q&A')], db_index=True, help_text='Collection type (clinical_records or icd10_codes)', max_length=50)),
                ('document_id', models.CharField(db_index=True, help_text='Original document ID (UUID or code)', max_length=255)),
                ('document_text', models.TextField(help_text='Full text content of the document')),
                ('embedding', pgvector.django.vector.VectorField(dimensions=768, help_text='Vector embedding of the document')),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Additional metadata (patient_id, visit_code, diagnosis, etc.)')),
            ],
            options={
                'verbose_name': 'Vector Document',
                'verbose_name_plural': 'Vector Documents',
                'indexes': [models.Index(fields=['collection', 'document_id'], name='rag_service_collect_658e46_idx'), models.Index(fields=['collection', 'created_at'], name='rag_service_collect_a97822_idx')],
                'unique_together': {('collection', 'document_id')},
            },
        ),
    ]
