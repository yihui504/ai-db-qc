"""Test extreme filter conditions on all vector databases."""
import sys
import numpy as np

def test_pgvector_extreme():
    from adapters.pgvector_adapter import PgvectorAdapter
    
    adapter = PgvectorAdapter({
        'container': 'pgvector',
        'database': 'vectordb',
        'user': 'postgres',
        'password': 'pgvector'
    })
    coll_name = 'extreme_filter_test'
    
    # Setup
    try:
        adapter.drop_collection(coll_name)
    except:
        pass
    adapter.create_collection(coll_name, dim=64)
    vectors = [np.random.rand(64).astype(np.float32) for _ in range(100)]
    adapter.insert(coll_name, vectors, [{'id': i, 'val': i} for i in range(100)])
    adapter.build_index(coll_name)
    
    print("\n=== PGVECTOR EXTREME FILTER TESTS ===")
    
    # Test 1: Empty result filter
    result = adapter.filtered_search(coll_name, vectors[0], top_k=10, filter_expr='val > 1000')
    print(f"Test1 (empty result): {len(result)} results (expected 0) - {'PASS' if len(result) == 0 else 'VIOLATION'}")
    
    # Test 2: Single match
    result = adapter.filtered_search(coll_name, vectors[0], top_k=10, filter_expr='val = 50')
    print(f"Test2 (single match): {len(result)} results (expected 1) - {'PASS' if len(result) >= 1 else 'VIOLATION'}")
    
    # Test 3: All match
    result = adapter.filtered_search(coll_name, vectors[0], top_k=10, filter_expr='val >= 0')
    print(f"Test3 (all match): {len(result)} results (expected 10) - {'PASS' if len(result) >= 10 else 'VIOLATION'}")
    
    # Test 4: Zero vector
    zero_vec = np.zeros(64, dtype=np.float32)
    result = adapter.search(coll_name, zero_vec, top_k=5)
    print(f"Test4 (zero vector): {len(result)} results - {'PASS' if len(result) == 5 else 'VIOLATION'}")
    
    # Test 5: Negative filter
    result = adapter.filtered_search(coll_name, vectors[0], top_k=10, filter_expr='val < 0')
    print(f"Test5 (negative filter): {len(result)} results (expected 0) - {'PASS' if len(result) == 0 else 'VIOLATION'}")
    
    adapter.drop_collection(coll_name)
    print("pgvector tests completed")

def test_qdrant_extreme():
    from adapters.qdrant_adapter import QdrantAdapter
    
    adapter = QdrantAdapter({'host': 'localhost', 'port': 6333})
    coll_name = 'extreme_filter_test'
    
    # Setup
    try:
        adapter.drop_collection(coll_name)
    except:
        pass
    adapter.create_collection(coll_name, dim=64)
    vectors = [np.random.rand(64).astype(np.float32) for _ in range(100)]
    adapter.insert(coll_name, vectors, [{'id': i, 'val': i} for i in range(100)])
    adapter.build_index(coll_name)
    
    print("\n=== QDRANT EXTREME FILTER TESTS ===")
    
    # Test 1: Empty result filter
    result = adapter.filtered_search(coll_name, vectors[0].tolist(), top_k=10, filter_expr='val > 1000')
    print(f"Test1 (empty result): {len(result)} results (expected 0) - {'PASS' if len(result) == 0 else 'VIOLATION'}")
    
    # Test 2: Single match
    result = adapter.filtered_search(coll_name, vectors[0].tolist(), top_k=10, filter_expr='val == 50')
    print(f"Test2 (single match): {len(result)} results (expected 1) - {'PASS' if len(result) >= 1 else 'VIOLATION'}")
    
    # Test 3: All match
    result = adapter.filtered_search(coll_name, vectors[0].tolist(), top_k=10, filter_expr='val >= 0')
    print(f"Test3 (all match): {len(result)} results (expected 10) - {'PASS' if len(result) >= 10 else 'VIOLATION'}")
    
    # Test 4: Zero vector
    zero_vec = np.zeros(64, dtype=np.float32).tolist()
    result = adapter.search(coll_name, zero_vec, top_k=5)
    print(f"Test4 (zero vector): {len(result)} results - {'PASS' if len(result) == 5 else 'VIOLATION'}")
    
    # Test 5: Negative filter
    result = adapter.filtered_search(coll_name, vectors[0].tolist(), top_k=10, filter_expr='val < 0')
    print(f"Test5 (negative filter): {len(result)} results (expected 0) - {'PASS' if len(result) == 0 else 'VIOLATION'}")
    
    adapter.drop_collection(coll_name)
    print("qdrant tests completed")

def test_weaviate_extreme():
    from adapters.weaviate_adapter import WeaviateAdapter
    
    adapter = WeaviateAdapter({'host': 'localhost', 'port': 8080})
    coll_name = 'extreme_filter_test'
    
    # Setup
    try:
        adapter.drop_collection(coll_name)
    except:
        pass
    adapter.create_collection(coll_name, dim=64)
    vectors = [np.random.rand(64).astype(np.float32) for _ in range(100)]
    adapter.insert(coll_name, vectors, [{'id': str(i), 'val': i} for i in range(100)])
    adapter.build_index(coll_name)
    
    print("\n=== WEAVIATE EXTREME FILTER TESTS ===")
    
    # Test 1: Empty result filter
    result = adapter.filtered_search(coll_name, vectors[0].tolist(), top_k=10, filter_expr='val > 1000')
    print(f"Test1 (empty result): {len(result)} results (expected 0) - {'PASS' if len(result) == 0 else 'VIOLATION'}")
    
    # Test 2: Single match
    result = adapter.filtered_search(coll_name, vectors[0].tolist(), top_k=10, filter_expr='val == 50')
    print(f"Test2 (single match): {len(result)} results (expected 1) - {'PASS' if len(result) >= 1 else 'VIOLATION'}")
    
    # Test 3: All match
    result = adapter.filtered_search(coll_name, vectors[0].tolist(), top_k=10, filter_expr='val >= 0')
    print(f"Test3 (all match): {len(result)} results (expected 10) - {'PASS' if len(result) >= 10 else 'VIOLATION'}")
    
    # Test 4: Zero vector
    zero_vec = np.zeros(64, dtype=np.float32).tolist()
    result = adapter.search(coll_name, zero_vec, top_k=5)
    print(f"Test4 (zero vector): {len(result)} results - {'PASS' if len(result) == 5 else 'VIOLATION'}")
    
    # Test 5: Negative filter
    result = adapter.filtered_search(coll_name, vectors[0].tolist(), top_k=10, filter_expr='val < 0')
    print(f"Test5 (negative filter): {len(result)} results (expected 0) - {'PASS' if len(result) == 0 else 'VIOLATION'}")
    
    adapter.drop_collection(coll_name)
    print("weaviate tests completed")

if __name__ == '__main__':
    test_pgvector_extreme()
    test_qdrant_extreme()
    test_weaviate_extreme()
    print("\n=== ALL EXTREME FILTER TESTS COMPLETED ===")
