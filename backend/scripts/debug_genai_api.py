
import os
import inspect
from django.conf import settings

# Setup Django standalone
if not settings.configured:
    import sys
    # Add backend to path
    backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_path not in sys.path:
        sys.path.append(backend_path)
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()

def inspect_api():
    try:
        import google.genai as genai
        print("Imported google.genai successfully")
        
        api_key = getattr(settings, 'GOOGLE_API_KEY', None) or os.environ.get('GOOGLE_API_KEY')
        client = genai.Client(api_key=api_key)
        print("Created client")
        
        method = client.models.embed_content
        print(f"Method: {method}")
        print(f"Signature: {inspect.signature(method)}")
        print(f"Docstring: {method.__doc__}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_api()
