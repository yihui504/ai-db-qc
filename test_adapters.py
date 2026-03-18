"""Quick adapter health check."""
import sys
sys.path.insert(0, ".")

from adapters.milvus_adapter import MilvusAdapter
from adapters.weaviate_adapter import WeaviateAdapter
from adapters.pgvector_adapter import PgvectorAdapter

print("Testing adapters...")

# Milvus
try:
    a = MilvusAdapter({"host": "localhost", "port": 19530})
    print(f"Milvus health: {a.health_check()}")
except Exception as e:
    print(f"Milvus error: {e}")

# Weaviate
try:
    a = WeaviateAdapter({"host": "localhost", "port": 8080})
    print(f"Weaviate health: {a.health_check()}")
except Exception as e:
    print(f"Weaviate error: {e}")

# Pgvector
try:
    a = PgvectorAdapter({"container": "pgvector", "database": "vectordb", "user": "postgres", "password": "pgvector"})
    print(f"Pgvector health: {a.health_check()}")
except Exception as e:
    print(f"Pgvector error: {e}")
