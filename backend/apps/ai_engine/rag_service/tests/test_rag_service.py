"""
Integration tests for RAG service.

Run with: python manage.py test apps.ai_engine.rag_service.tests
"""

from django.test import TestCase
import asyncio

from apps.ai_engine.rag_service.embeddings import EmbeddingService, embed_clinical_note
from apps.ai_engine.rag_service.vector_service import VectorService
from apps.ai_engine.rag_service.context_retrieval import retrieve_patient_context, format_context_for_llm
from apps.ai_engine.rag_service.hybrid_search import HybridSearchService

class EmbeddingServiceTest(TestCase):
    """Test embedding generation."""
    
    def setUp(self):
        self.embedding_service = EmbeddingService(provider='sentence-transformers')
    
    def test_embed_text(self):
        """Test basic text embedding."""
        async def _test():
            text = "Bệnh nhân bị đau đầu và sốt cao"
            embedding = await self.embedding_service.embed_text(text)
            
            # Check embedding is valid
            self.assertIsInstance(embedding, list)
            self.assertGreater(len(embedding), 0)
            self.assertEqual(len(embedding), self.embedding_service.get_embedding_dimension())
        
        asyncio.run(_test())
    
    def test_embed_clinical_note(self):
        """Test clinical note embedding."""
        async def _test():
            embedding = await embed_clinical_note(
                chief_complaint="Đau đầu, sốt cao",
                history_of_present_illness="Bệnh nhân bị sốt từ 3 ngày trước",
                physical_exam="Nhiệt độ 39°C, huyết áp bình thường",
                embedding_service=self.embedding_service
            )
            
            self.assertIsInstance(embedding, list)
            self.assertGreater(len(embedding), 0)
        
        asyncio.run(_test())
    
    def test_embedding_cache(self):
        """Test that embeddings are cached."""
        async def _test():
            text = "Đau bụng quặn, tiêu chảy"
            
            # First embedding
            embedding1 = await self.embedding_service.embed_text(text)
            
            # Second embedding (should be from cache)
            embedding2 = await self.embedding_service.embed_text(text)
            
            # Should be identical
            self.assertEqual(embedding1, embedding2)
        
        asyncio.run(_test())


class VectorServiceTest(TestCase):
    """Test vector storage and search."""
    
    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        self.vector_service = VectorService(persist_directory=self.temp_dir)
        self.embedding_service = EmbeddingService(provider='sentence-transformers')
    
    def test_add_and_search_documents(self):
        """Test adding documents and semantic search."""
        async def _test():
            # Prepare test data
            documents = [
                "Bệnh nhân bị đau đầu và sốt cao",
                "Bệnh nhân ho khan, khó thở",
                "Bệnh nhân đau bụng dưới bên phải"
            ]
            
            # Generate embeddings
            embeddings = []
            for doc in documents:
                emb = await self.embedding_service.embed_text(doc)
                embeddings.append(emb)
            
            # Add to vector DB
            await self.vector_service.add_documents(
                collection_name='test_collection',
                documents=documents,
                embeddings=embeddings,
                ids=['doc1', 'doc2', 'doc3']
            )
            
            # Test search
            query = "triệu chứng sốt"
            query_embedding = await self.embedding_service.embed_text(query)
            
            results = await self.vector_service.semantic_search(
                collection_name='test_collection',
                query_embedding=query_embedding,
                top_k=2
            )
            
            # Verify results
            self.assertGreater(len(results), 0)
            self.assertIn('similarity', results[0])
            self.assertIn('document', results[0])
        
        asyncio.run(_test())
    
    def test_update_documents(self):
        """Test updating existing documents."""
        async def _test():
            # Add initial document
            doc = "Bệnh nhân bị sốt"
            emb = await self.embedding_service.embed_text(doc)
            
            await self.vector_service.add_documents(
                collection_name='test_update',
                documents=[doc],
                embeddings=[emb],
                ids=['doc1']
            )
            
            # Update document
            updated_doc = "Bệnh nhân bị sốt cao và đau đầu"
            updated_emb = await self.embedding_service.embed_text(updated_doc)
            
            success = await self.vector_service.update_documents(
                collection_name='test_update',
                documents=[updated_doc],
                embeddings=[updated_emb],
                ids=['doc1']
            )
            
            self.assertTrue(success)
        
        asyncio.run(_test())


class HybridSearchTest(TestCase):
    """Test hybrid search functionality."""
    
    def setUp(self):
        self.search_service = HybridSearchService()
    
    def test_search_icd10_by_code(self):
        """Test keyword search for ICD-10 codes."""
        # This test requires ICD-10 data in the database
        # Skip if no data available
        from apps.core_services.core.models import ICD10Code
        
        if not ICD10Code.objects.exists():
            self.skipTest("No ICD-10 data available")
        
        async def _test():
            results = await self.search_service.search_icd10_by_code(
                code_query="J",
                exact_match=False,
                top_k=5
            )
            
            # Verify results
            if len(results) > 0:
                self.assertIn('code', results[0])
                self.assertIn('name', results[0])
                self.assertTrue(results[0]['code'].startswith('J'))
        
        asyncio.run(_test())


class PIIMaskingTest(TestCase):
    """Test PII masking utilities."""
    
    def test_mask_patient_id(self):
        """Test patient ID masking."""
        from apps.ai_engine.rag_service.pii_masking import mask_patient_id
        
        patient_id = "12345678-1234-1234-1234-123456789012"
        masked = mask_patient_id(patient_id)
        
        self.assertNotEqual(masked, patient_id)
        self.assertTrue(masked.startswith('P_'))
    
    def test_mask_sensitive_fields(self):
        """Test masking of sensitive fields in dict."""
        from apps.ai_engine.rag_service.pii_masking import mask_sensitive_fields
        
        data = {
            'patient_id': '12345',
            'id_card': '123456789',
            'insurance_number': 'AB123456789',
            'contact_number': '0123456789',
            'name': 'Nguyễn Văn A'
        }
        
        masked = mask_sensitive_fields(data)
        
        # Sensitive fields should be masked
        self.assertNotEqual(masked['id_card'], data['id_card'])
        self.assertNotEqual(masked['insurance_number'], data['insurance_number'])
        self.assertNotEqual(masked['contact_number'], data['contact_number'])
        
        # Non-sensitive fields should remain
        self.assertEqual(masked['name'], data['name'])
