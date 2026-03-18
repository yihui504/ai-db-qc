"""Debug Weaviate setup for semantic extended test."""
import sys
sys.path.insert(0, ".")

from adapters.weaviate_adapter import WeaviateAdapter
import hashlib

def _embed_texts_hash(texts, dim=384):
    vectors = []
    for text in texts:
        h = hashlib.sha256(text.encode()).hexdigest()
        raw = [int(h[i:i+2], 16) for i in range(0, min(len(h), dim * 2), 2)]
        vec = [(x - 127.5) / 127.5 for x in raw[:dim]]
        while len(vec) < dim:
            vec.append(0.0)
        vectors.append(vec[:dim])
    return vectors

# Create adapter
adapter = WeaviateAdapter({"host": "localhost", "port": 8080})

# Test texts
texts = [
    "The company reported strong quarterly earnings growth.",
    "The firm achieved significant profit increases this quarter.",
    "The stock price fell sharply after the earnings report.",
]

# Embed
dim = 4  # Use smaller dim for Weaviate
vecs = _embed_texts_hash(texts, dim)
print(f"Vectors: {len(vecs)}, dim: {len(vecs[0])}")

# Create collection
col = "debug_test"
r = adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
print(f"Drop: {r.get('status')}")

r = adapter.execute({"operation": "create_collection", "params": {"collection_name": col, "dimension": dim}})
print(f"Create: {r}")

# Insert
r = adapter.execute({"operation": "insert", "params": {"collection_name": col, "vectors": vecs}})
print(f"Insert: {r}")

# Flush
r = adapter.execute({"operation": "flush", "params": {"collection_name": col}})
print(f"Flush: {r}")

# Build index
r = adapter.execute({"operation": "build_index", "params": {"collection_name": col}})
print(f"Build index: {r}")

# Load
r = adapter.execute({"operation": "load", "params": {"collection_name": col}})
print(f"Load: {r}")

# Search
query = vecs[0]
r = adapter.execute({"operation": "search", "params": {"collection_name": col, "vector": query, "top_k": 3}})
print(f"Search: {r}")

# Cleanup
r = adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
print(f"Drop: {r}")
