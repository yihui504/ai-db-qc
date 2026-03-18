"""Test Milvus extreme conditions."""
import numpy as np
from adapters.milvus_adapter import MilvusAdapter

def test_milvus_repeated_delete():
    adapter = MilvusAdapter({'host': 'localhost', 'port': 19530})
    coll = 'stress_delete_test'
    
    # Setup
    try:
        adapter.drop_collection(coll)
    except:
        pass
    adapter.create_collection(coll, dim=64)
    
    # Insert 200 vectors
    vectors = np.random.rand(200, 64).astype(np.float32)
    adapter.insert(coll, vectors, [{'id': i} for i in range(200)])
    adapter.flush(coll)
    
    info = adapter.get_collection_info(coll)
    print(f"After insert: entity_count = {info.get('entity_count', 'N/A')}")
    
    # Delete 100
    delete_expr = 'id in [' + ','.join(str(i) for i in range(100)) + ']'
    adapter.delete(coll, delete_expr)
    adapter.flush(coll)
    
    info = adapter.get_collection_info(coll)
    print(f"After delete 100: entity_count = {info.get('entity_count', 'N/A')}")
    print(f"Expected: 100, Actual may show: 200 (DEF-001 lazy compaction bug)")
    
    # Delete remaining
    delete_expr = 'id in [' + ','.join(str(i) for i in range(100, 200)) + ']'
    adapter.delete(coll, delete_expr)
    adapter.flush(coll)
    
    info = adapter.get_collection_info(coll)
    print(f"After delete all: entity_count = {info.get('entity_count', 'N/A')}")
    print(f"Expected: 0, Actual may show: 200 (lazy compaction bug)")
    
    adapter.drop_collection(coll)
    print("Milvus stress delete test completed")

def test_milvus_empty_query():
    adapter = MilvusAdapter({'host': 'localhost', 'port': 19530})
    coll = 'empty_query_test'
    
    try:
        adapter.drop_collection(coll)
    except:
        pass
    adapter.create_collection(coll, dim=64)
    adapter.build_index(coll)
    
    # Empty vector search
    zero_vec = np.zeros(64, dtype=np.float32)
    result = adapter.search(coll, zero_vec.tolist(), top_k=5)
    print(f"Empty vector search: {len(result)} results")
    
    # Search with no collection
    result = adapter.search(coll, [0.1]*64, top_k=5)
    print(f"Normal search: {len(result)} results")
    
    adapter.drop_collection(coll)
    print("Milvus empty query test completed")

if __name__ == '__main__':
    test_milvus_repeated_delete()
    test_milvus_empty_query()
    print("\n=== ALL MILVUS EXTREME TESTS COMPLETED ===")
