import os
import asyncio
import logging
import sys
import numpy as np
from typing import List

# Setup Django standalone
if __name__ == "__main__":
    backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_path not in sys.path:
        sys.path.append(backend_path)
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        import django
        from django.conf import settings
        if not settings.configured:
            django.setup()
    except ImportError:
        pass

# Import after setup
try:
    from apps.ai_engine.rag_service.embeddings import EmbeddingService
except ImportError:
    pass

# Configure logging
logging.basicConfig(level=logging.INFO)

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    vec1 = np.array(v1)
    vec2 = np.array(v2)
    
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
        
    return np.dot(vec1, vec2) / (norm1 * norm2)

async def run_quality_test():
    """Test semantic search quality of embeddings."""
    print("--- Starting Semantic Quality Test ---")
    
    service = EmbeddingService(provider='google')
    print(f"Model: {service.model_name}")

    # 1. Define a corpus of mixed topics
    documents = [
        "Patient presents with severe headache and nausea.", # 0: Clinical/Neurology
        "The patient has a history of type 2 diabetes and hypertension.", # 1: Clinical/Chronic
        "The stock market crashed today due to unexpected inflation data.", # 2: Finance (Unrelated)
        "Barcelona defeated Real Madrid in the El Clasico match yesterday.", # 3: Sports (Unrelated)
        "Python is a high-level programming language known for its readability.", # 4: Tech (Unrelated)
    ]
    
    # 2. Define queries targeting specific documents
    test_cases = [
        {
            "query": "symptoms of migraine or head pain",
            "expected_index": 0,
            "description": "Clinical Symptom Search"
        },
        {
            "query": "high blood pressure and sugar levels",
            "expected_index": 1,
            "description": "Clinical Disease Search"
        },
        {
            "query": "coding in python",
            "expected_index": 4,
            "description": "Tech Search"
        }
    ]

    print(f"\nEmbedding {len(documents)} documents...")
    doc_embeddings = await service.embed_batch(documents)
    
    for case in test_cases:
        query = case["query"]
        expected_idx = case["expected_index"]
        desc = case["description"]
        
        print(f"\n-------------------------------------------")
        print(f"Test Case: {desc}")
        print(f"Query: '{query}'")
        
        # Embed query
        query_vec = await service.embed_text(query)
        
        # Calculate similarities
        scores = []
        for i, doc_vec in enumerate(doc_embeddings):
            score = cosine_similarity(query_vec, doc_vec)
            scores.append((score, i))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[0], reverse=True)
        
        # Print top 3 matches
        print("Top matches:")
        top_match_index = scores[0][1]
        for score, idx in scores[:3]:
            print(f"  {score:.4f} | {documents[idx][:60]}...")
            
        # Verify
        if top_match_index == expected_idx:
            print(f"✅ PASSED: Top match is correct.")
        else:
            print(f"❌ FAILED: Expected index {expected_idx}, got {top_match_index}")
            print(f"   Expected doc: {documents[expected_idx]}")

def run():
    asyncio.run(run_quality_test())

if __name__ == "__main__":
    run()
