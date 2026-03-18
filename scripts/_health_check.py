"""Quick health check for Milvus and Qdrant."""
import sys
sys.path.insert(0, '.')

milvus_ok = False
qdrant_ok = False

try:
    from adapters.milvus_adapter import MilvusAdapter
    a = MilvusAdapter({"host": "localhost", "port": 19530})
    milvus_ok = a.health_check()
    print(f"Milvus: {'OK' if milvus_ok else 'FAIL'}")
except Exception as e:
    print(f"Milvus: ERROR - {e}")

try:
    from adapters.qdrant_adapter import QdrantAdapter
    b = QdrantAdapter({"url": "http://localhost:6333"})
    qdrant_ok = b.health_check()
    print(f"Qdrant: {'OK' if qdrant_ok else 'FAIL'}")
except Exception as e:
    print(f"Qdrant: ERROR - {e}")

# Check sentence-transformers
try:
    from ai_db_qa.embedding import get_backend_info
    info = get_backend_info()
    st = info["sentence_transformers"]["available"]
    print(f"sentence-transformers: {'available' if st else 'not installed'}")
except Exception as e:
    print(f"embedding module: ERROR - {e}")
