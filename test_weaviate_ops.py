"""Quick test for Weaviate adapter operations."""
import sys
sys.path.insert(0, ".")

from adapters.weaviate_adapter import WeaviateAdapter
import random

# Create adapter
adapter = WeaviateAdapter({"host": "localhost", "port": 8080})
print("Adapter created")

# Test create collection
col = "test_col"
result = adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
print(f"Drop: {result}")

result = adapter.execute({"operation": "create_collection", "params": {"collection_name": col, "dimension": 4}})
print(f"Create: {result}")

# Test insert
vectors = [[random.random() for _ in range(4)] for _ in range(10)]
result = adapter.execute({"operation": "insert", "params": {"collection_name": col, "vectors": vectors}})
print(f"Insert: {result}")

# Test flush
result = adapter.execute({"operation": "flush", "params": {"collection_name": col}})
print(f"Flush: {result}")

# Test build index
result = adapter.execute({"operation": "build_index", "params": {"collection_name": col, "index_type": "hnsw", "metric_type": "cosine"}})
print(f"Build index: {result}")

# Test load
result = adapter.execute({"operation": "load", "params": {"collection_name": col}})
print(f"Load: {result}")

# Test search
query_vec = vectors[0]
result = adapter.execute({"operation": "search", "params": {"collection_name": col, "vector": query_vec, "top_k": 3}})
print(f"Search: {result}")

# Test drop
result = adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
print(f"Drop: {result}")
