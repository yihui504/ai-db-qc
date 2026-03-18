"""Check Weaviate connection and run basic tests."""
import sys
sys.path.insert(0, '.')

from adapters.weaviate_adapter import WeaviateAdapter

adapter = WeaviateAdapter({'url': 'http://localhost:8080'})
try:
    health = adapter.health_check()
    print('Weaviate Health:', health)
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
