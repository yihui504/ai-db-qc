#!/usr/bin/env python3
"""Quick test for Qdrant filtered_search."""
import sys
sys.path.insert(0, '.')

from adapters.qdrant_adapter import QdrantAdapter

print("Testing Qdrant filtered_search...")
adapter = QdrantAdapter({'url': 'http://localhost:6333'})

# Create collection
adapter.execute({
    'operation': 'drop_collection',
    'params': {'collection_name': 'test_filter'}
})
adapter.execute({
    'operation': 'create_collection',
    'params': {'collection_name': 'test_filter', 'dimension': 64}
})

# Insert test data
vectors = [[0.1] * 64, [0.2] * 64, [0.3] * 64]
scalar_data = [
    {'id': 0, 'score': 10},
    {'id': 1, 'score': 50},
    {'id': 2, 'score': 90},
]
adapter.execute({
    'operation': 'insert',
    'params': {
        'collection_name': 'test_filter',
        'vectors': vectors,
        'ids': [0, 1, 2],
        'scalar_data': scalar_data
    }
})

# Test simple filter
print("\nTest 1: Simple filter (score == 50)")
r = adapter.execute({
    'operation': 'filtered_search',
    'params': {
        'collection_name': 'test_filter',
        'vector': [0.1] * 64,
        'top_k': 10,
        'filter': {'score': 50}
    }
})
print(f"Result: {r}")

# Test range filter
print("\nTest 2: Range filter (score > 50)")
r = adapter.execute({
    'operation': 'filtered_search',
    'params': {
        'collection_name': 'test_filter',
        'vector': [0.1] * 64,
        'top_k': 10,
        'filter': {'score': {'gt': 50}}
    }
})
print(f"Result: {r}")

# Test range combination
print("\nTest 3: Range filter (30 <= score <= 80)")
r = adapter.execute({
    'operation': 'filtered_search',
    'params': {
        'collection_name': 'test_filter',
        'vector': [0.1] * 64,
        'top_k': 10,
        'filter': {'score': {'gte': 30, 'lte': 80}}
    }
})
print(f"Result: {r}")

# Cleanup
adapter.execute({
    'operation': 'drop_collection',
    'params': {'collection_name': 'test_filter'}
})

print("\nAll tests completed!")
