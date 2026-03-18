#!/usr/bin/env python3
"""Quick test for Weaviate connection."""
import sys
sys.path.insert(0, '.')

from adapters.weaviate_adapter import WeaviateAdapter

print("Testing Weaviate connection...")
adapter = WeaviateAdapter({'url': 'http://localhost:8080'})
print("Adapter created")

health = adapter.health_check()
print(f"Health check: {health}")
