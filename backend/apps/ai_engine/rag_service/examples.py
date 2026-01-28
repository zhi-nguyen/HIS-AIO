"""
Example usage of RAG Service for Healthcare Information System.

This script demonstrates how to use the RAG service components.
"""

import asyncio
from apps.ai_engine.rag_service import (
    VectorService,
    EmbeddingService,
    HybridSearchService,
    retrieve_patient_context,
    format_context_for_llm
)


async def example_patient_context_retrieval():
    """Example: Retrieve patient context for LLM."""
    print("\n=== Example 1: Patient Context Retrieval ===\n")
    
    # Replace with actual patient ID from your database
    patient_id = "PATIENT_UUID_HERE"
    
    # Retrieve context
    context = await retrieve_patient_context(
        patient_id=patient_id,
        query="triệu chứng sốt",  # Optional semantic search query
        top_k_records=5
    )
    
    # Format for LLM
    formatted_context = format_context_for_llm(context, include_pii=True)
    
    print(formatted_context)
    print(f"\n✓ Retrieved context for patient {context['demographics'].get('patient_code')}")


async def example_hybrid_search():
    """Example: Hybrid search for ICD-10 codes."""
    print("\n=== Example 2: Hybrid Search for ICD-10 Codes ===\n")
    
    search_service = HybridSearchService()
    
    # Search by symptoms (semantic search prioritized)
    print("Searching for: 'đau đầu, sốt cao'")
    results = await search_service.hybrid_search(
        query="đau đầu, sốt cao",
        top_k=5
    )
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['code']} - {result['name']}")
        print(f"   Score: {result['rrf_score']:.4f}")
        print(f"   Search type: {result['search_type']}")
    
    # Search by code (keyword search prioritized)
    print("\n\nSearching for: 'J00'")
    results = await search_service.hybrid_search(
        query="J00",
        top_k=5
    )
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['code']} - {result['name']}")
        print(f"   Score: {result['rrf_score']:.4f}")


async def example_semantic_search_clinical_records():
    """Example: Semantic search in clinical records."""
    print("\n=== Example 3: Semantic Search Clinical Records ===\n")
    
    vector_service = VectorService()
    embedding_service = EmbeddingService()
    
    # Search query
    query = "bệnh nhân bị tiểu đường"
    
    # Generate query embedding
    query_embedding = await embedding_service.embed_text(query)
    
    # Search
    results = await vector_service.semantic_search(
        collection_name='clinical_records',
        query_embedding=query_embedding,
        top_k=5,
        similarity_threshold=0.5
    )
    
    print(f"Query: '{query}'")
    print(f"Found {len(results)} relevant clinical records:\n")
    
    for i, result in enumerate(results, 1):
        metadata = result.get('metadata', {})
        print(f"{i}. Visit: {metadata.get('visit_code')}")
        print(f"   Date: {metadata.get('created_at')}")
        print(f"   Chief Complaint: {metadata.get('chief_complaint')}")
        print(f"   Similarity: {result.get('similarity'):.4f}\n")


async def example_add_clinical_record_to_vector_db():
    """Example: Add a new clinical record to vector database."""
    print("\n=== Example 4: Add Clinical Record to Vector DB ===\n")
    
    from apps.ai_engine.rag_service.data_loader import update_clinical_record_in_vector_db
    
    # Replace with actual record ID
    record_id = "RECORD_UUID_HERE"
    
    success = await update_clinical_record_in_vector_db(record_id)
    
    if success:
        print(f"✓ Successfully added/updated record {record_id} in vector database")
    else:
        print(f"✗ Failed to add/update record {record_id}")


async def example_embedding_generation():
    """Example: Generate embeddings for clinical text."""
    print("\n=== Example 5: Embedding Generation ===\n")
    
    embedding_service = EmbeddingService(provider='sentence-transformers')
    
    # Single text embedding
    text = "Bệnh nhân bị đau bụng quặn, tiêu chảy kéo dài 3 ngày"
    embedding = await embedding_service.embed_text(text)
    
    print(f"Text: '{text}'")
    print(f"Embedding dimension: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")
    
    # Batch embedding
    texts = [
        "Sốt cao 39°C",
        "Ho khan, khó thở",
        "Đau ngực trái"
    ]
    
    embeddings = await embedding_service.embed_batch(texts)
    print(f"\n✓ Generated {len(embeddings)} embeddings in batch")


async def main():
    """Run all examples."""
    print("="*60)
    print("RAG Service Usage Examples")
    print("="*60)
    
    # Run examples
    try:
        await example_embedding_generation()
        # await example_patient_context_retrieval()  # Requires patient data
        # await example_hybrid_search()  # Requires ICD-10 data
        # await example_semantic_search_clinical_records()  # Requires indexed records
        # await example_add_clinical_record_to_vector_db()  # Requires record data
        
    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
