"""Test database connections."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_milvus():
    try:
        from adapters.milvus_adapter import MilvusAdapter
        a = MilvusAdapter()
        a.connect(host='localhost', port=19530)
        print("Milvus: OK")
        return True
    except Exception as e:
        print(f"Milvus: FAILED - {e}")
        return False

def test_qdrant():
    try:
        from adapters.qdrant_adapter import QdrantAdapter
        a = QdrantAdapter()
        a.connect(url='http://localhost:6333')
        print("Qdrant: OK")
        return True
    except Exception as e:
        print(f"Qdrant: FAILED - {e}")
        return False

def test_weaviate():
    try:
        from adapters.weaviate_adapter import WeaviateAdapter
        a = WeaviateAdapter()
        a.connect(host='localhost', port=8080)
        print("Weaviate: OK")
        return True
    except Exception as e:
        print(f"Weaviate: FAILED - {e}")
        return False

def test_pgvector():
    try:
        from adapters.pgvector_adapter import PgvectorAdapter
        a = PgvectorAdapter()
        a.connect(container_name='pgvector', db_name='vectordb')
        print("pgvector: OK")
        return True
    except Exception as e:
        print(f"pgvector: FAILED - {e}")
        return False

if __name__ == "__main__":
    print("Testing database connections...\n")
    results = []
    results.append(("Milvus", test_milvus()))
    results.append(("Qdrant", test_qdrant()))
    results.append(("Weaviate", test_weaviate()))
    results.append(("pgvector", test_pgvector()))
    
    print("\n" + "="*40)
    print("Connection Test Summary")
    print("="*40)
    for name, ok in results:
        status = "[OK]" if ok else "[FAIL]"
        print(f"{status} {name}")
    
    all_ok = all(r[1] for r in results)
    sys.exit(0 if all_ok else 1)
