"""Test Weaviate Hybrid Search Filter - GitHub Issue #7681.

Testing whether Weaviate hybrid search (BM25 + vector) correctly applies filters.
"""
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from adapters.weaviate_adapter import WeaviateAdapter


def test_weaviate_hybrid_filter():
    """Test hybrid search with filters."""
    adapter = WeaviateAdapter({"url": "http://localhost:8080"})
    
    if not adapter.health_check():
        print("Weaviate is not available!")
        return

    collection = "hybrid_filter_test"
    
    # Cleanup
    try:
        adapter.execute({"operation": "drop_collection", "params": {"collection_name": collection}})
    except:
        pass
    
    # Create collection with text properties
    adapter.execute({
        "operation": "create_collection",
        "params": {
            "collection_name": collection,
            "dimension": 384,
            "properties": [
                {"name": "text", "data_type": "text"},
                {"name": "category", "data_type": "text"}
            ]
        }
    })
    
    # Insert test data
    test_data = [
        {"id": 1, "text": "machine learning algorithms", "category": "tech"},
        {"id": 2, "text": "deep neural networks", "category": "tech"},
        {"id": 3, "text": "cooking recipes for dinner", "category": "food"},
        {"id": 4, "text": "healthy eating habits", "category": "food"},
    ]
    
    for item in test_data:
        adapter.execute({
            "operation": "insert",
            "params": {
                "collection_name": collection,
                "vectors": [[0.1] * 384],  # placeholder vectors
                "ids": [item["id"]],
                "payloads": [{"text": item["text"], "category": item["category"]}]
            }
        })
    
    print("Test 1: Regular filtered search")
    try:
        result = adapter.execute({
            "operation": "filtered_search",
            "params": {
                "collection_name": collection,
                "vector": [0.1] * 384,
                "filter": {"category": "tech"},
                "top_k": 10
            }
        })
        print(f"  Results: {len(result.get('data', []))}")
        for r in result.get('data', []):
            print(f"    - id={r['id']}, category={r.get('payload', {}).get('category')}")
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\nTest 2: Hybrid search with filter (if supported)")
    # Note: Weaviate adapter may not support hybrid search yet
    # This is a placeholder for future implementation
    try:
        result = adapter.execute({
            "operation": "hybrid_search",
            "params": {
                "collection_name": collection,
                "query": "learning",
                "filter": {"category": "tech"},
                "top_k": 10
            }
        })
        print(f"  Results: {len(result.get('data', []))}")
    except Exception as e:
        print(f"  Not supported or error: {e}")
    
    # Cleanup
    try:
        adapter.execute({"operation": "drop_collection", "params": {"collection_name": collection}})
    except:
        pass
    
    print("\nDone.")


if __name__ == "__main__":
    test_weaviate_hybrid_filter()
