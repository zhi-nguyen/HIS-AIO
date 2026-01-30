import os
import asyncio
import logging
import sys

# Setup Django if running standalone - MUST be done before imports
if __name__ == "__main__":
    # Add backend to path
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

# Now import app modules
try:
    from django.conf import settings
    from apps.ai_engine.rag_service.embeddings import EmbeddingService
except ImportError:
    # If imports fail at top level (e.g. when imported as module without setup), 
    # they will be handled effectively when run() is called if setup was successful
    pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_test():
    """Test Google GenAI embedding validation."""
    # Re-import inside function to ensure django is setup if called via runscript
    from apps.ai_engine.rag_service.embeddings import EmbeddingService
    
    print("--- Starting Google GenAI Embedding Test ---")
    
    # Check API Key
    api_key = getattr(settings, 'GOOGLE_API_KEY', None) or os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("❌ FAILED: GOOGLE_API_KEY not found in settings or environment.")
        return

    print(f"✅ GOOGLE_API_KEY found: {api_key[:5]}...{api_key[-5:] if len(api_key)>10 else ''}")

    try:
        # Initialize Service
        print("\nInitializing EmbeddingService...")
        service = EmbeddingService(provider='google')
        print(f"✅ Service initialized with provider: {service.provider}")
        print(f"✅ Model name: {service.model_name}")

        # Test single embedding
        text = "This is a test sentence for clinical embedding."
        print(f"\nGenerating embedding for text: '{text}'")
        embedding = await service.embed_text(text)
        
        if embedding and isinstance(embedding, list) and len(embedding) > 0:
            print(f"✅ Embedding generated successfully.")
            print(f"✅ Dimension: {len(embedding)}")
            print(f"✅ First 5 values: {embedding[:5]}")
            
            expected_dim = service.get_embedding_dimension()
            if len(embedding) == expected_dim:
                print(f"✅ Dimension matches expected: {expected_dim}")
            else:
                print(f"⚠️ Dimension mismatch! Expected {expected_dim}, got {len(embedding)}")
        else:
            print("❌ FAILED: Embedding generation returned empty or invalid result.")

        # Test batch embedding
        print("\nTesting batch embedding...")
        texts = ["Patient has fever.", "Prescribed antibiotics."]
        embeddings = await service.embed_batch(texts)
        
        if len(embeddings) == 2:
            print(f"✅ Batch embedding generated {len(embeddings)} vectors.")
        else:
            print(f"❌ FAILED: Batch embedding returned {len(embeddings)} vectors, expected 2.")

    except Exception as e:
        print(f"\n❌ EXCEPTION OCCURRED: {e}")
        import traceback
        traceback.print_exc()

def run():
    """Run the async test in sync context."""
    # For django-extensions runscript, sys.path usually already correct
    # But if running standalone, the __main__ block handles it.
    asyncio.run(run_test())

if __name__ == "__main__":
    run()
