"""Test Qdrant DATETIME filter - GitHub Issue #7462.

Testing whether Qdrant accepts invalid datetime values in payload filters.
"""
import sys
import json
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from adapters.qdrant_adapter import QdrantAdapter

def test_datetime_filter():
    """Test DATETIME filter with various date formats."""
    adapter = QdrantAdapter({"url": "http://localhost:6333"})
    
    if not adapter.health_check():
        print("Qdrant is not available!")
        return

    collection = "datetime_filter_test"
    
    # Cleanup and create collection
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": collection}})
    adapter.execute({"operation": "create_collection", "params": {"collection_name": collection, "dimension": 64}})
    
    # Insert test data with various date formats
    test_data = [
        {"id": 1, "vector": [0.1] * 64, "date": "2024-01-01T00:00:00Z"},
        {"id": 2, "vector": [0.2] * 64, "date": "2024-06-15T12:30:00Z"},
        {"id": 3, "vector": [0.3] * 64, "date": "2024-12-31T23:59:59Z"},
    ]
    
    for item in test_data:
        adapter.execute({
            "operation": "insert",
            "params": {
                "collection_name": collection,
                "vectors": [item["vector"]],
                "ids": [item["id"]],
                "payloads": [{"date": item["date"]}]
            }
        })
    
    print("Test 1: Valid date filter (gte)")
    try:
        result = adapter.execute({
            "operation": "filtered_search",
            "params": {
                "collection_name": collection,
                "vector": [0.1] * 64,
                "filter": {"date": {"gte": "2024-06-01T00:00:00Z"}},
                "top_k": 10
            }
        })
        print(f"  Results: {len(result.get('data', []))}")
        print(f"  Data: {result.get('data', [])}")
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\nTest 2: Invalid date filter (year > 2500)")
    try:
        result = adapter.execute({
            "operation": "filtered_search",
            "params": {
                "collection_name": collection,
                "vector": [0.1] * 64,
                "filter": {"date": {"gte": "2500-01-01T00:00:00Z"}},
                "top_k": 10
            }
        })
        print(f"  Results: {len(result.get('data', []))}")
        # Qdrant might accept invalid dates silently
        if len(result.get('data', [])) > 0:
            print(f"  ⚠️ WARNING: Invalid date was accepted!")
    except Exception as e:
        print(f"  Expected error: {e}")
    
    # Cleanup
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": collection}})
    print("\nDone.")


if __name__ == "__main__":
    test_datetime_filter()
