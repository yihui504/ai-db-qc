#!/usr/bin/env python3
"""Quick test for Qdrant connection."""
import sys
sys.path.insert(0, '.')

from adapters.qdrant_adapter import QdrantAdapter

print("Testing Qdrant connection...")
adapter = QdrantAdapter({'url': 'http://localhost:6333'})
print("Adapter created")

health = adapter.health_check()
print(f"Health check: {health}")

if health:
    # Try to create collection
    r = adapter.execute({
        'operation': 'create_collection',
        'params': {'collection_name': 'test_quick', 'dimension': 64}
    })
    print(f"Create collection result: {r}")
    
    # Clean up
    adapter.execute({
        'operation': 'drop_collection',
        'params': {'collection_name': 'test_quick'}
    })
    print("Done")
else:
    print("Qdrant not available")
