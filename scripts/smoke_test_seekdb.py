"""Smoke test for real seekdb connection and basic operations.

Verifies:
1. connect/auth works
2. create collection works
3. insert works
4. basic search works
5. filtered search works (if supported)
6. cleanup works

Usage:
    python scripts/smoke_test_seekdb.py --api-endpoint <url> --api-key <key>
"""

import argparse
import os
import sys
from typing import Any, Dict, Tuple


def print_section(title: str):
    """Print a section header."""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(test_name: str, success: bool, details: str = ""):
    """Print test result."""
    status = "[OK] PASS" if success else "[FAIL] FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"       {details}")


def test_health_check(adapter) -> Tuple[bool, str]:
    """Test 1: Health check / connection."""
    try:
        result = adapter.health_check()
        if result:
            return True, "Connection successful"
        else:
            return False, "Health check returned False"
    except Exception as e:
        return False, f"Exception: {e}"


def test_create_collection(adapter, collection_name: str) -> Tuple[bool, str, Dict]:
    """Test 2: Create collection."""
    try:
        request = {
            "operation": "create_collection",
            "params": {
                "collection_name": collection_name,
                "dimension": 128,
                "metric_type": "L2"
            }
        }
        result = adapter.execute(request)

        if result.get("status") == "success":
            return True, "Collection created", result
        else:
            return False, f"Error: {result.get('error')}", result
    except Exception as e:
        return False, f"Exception: {e}", {}


def test_insert(adapter, collection_name: str) -> Tuple[bool, str, Dict]:
    """Test 3: Insert vectors."""
    try:
        # Create some simple test vectors
        vectors = [
            [0.1] * 128,
            [0.2] * 128,
            [0.3] * 128,
            [0.4] * 128,
            [0.5] * 128
        ]

        request = {
            "operation": "insert",
            "params": {
                "collection_name": collection_name,
                "vectors": vectors
            }
        }
        result = adapter.execute(request)

        if result.get("status") == "success":
            count = result.get("insert_count", len(vectors))
            return True, f"Inserted {count} vectors", result
        else:
            return False, f"Error: {result.get('error')}", result
    except Exception as e:
        return False, f"Exception: {e}", {}


def test_search(adapter, collection_name: str) -> Tuple[bool, str, Dict]:
    """Test 4: Basic vector search."""
    try:
        query_vector = [0.15] * 128

        request = {
            "operation": "search",
            "params": {
                "collection_name": collection_name,
                "vector": query_vector,
                "top_k": 3
            }
        }
        result = adapter.execute(request)

        if result.get("status") == "success":
            data = result.get("data", [])
            return True, f"Search returned {len(data)} results", result
        else:
            return False, f"Error: {result.get('error')}", result
    except Exception as e:
        return False, f"Exception: {e}", {}


def test_filtered_search(adapter, collection_name: str) -> Tuple[bool, str, Dict]:
    """Test 5: Filtered search (if supported)."""
    try:
        query_vector = [0.15] * 128

        request = {
            "operation": "filtered_search",
            "params": {
                "collection_name": collection_name,
                "vector": query_vector,
                "top_k": 3,
                "filter": "id >= 2"  # Only return results with id >= 2
            }
        }
        result = adapter.execute(request)

        if result.get("status") == "success":
            data = result.get("data", [])
            return True, f"Filtered search returned {len(data)} results", result
        else:
            # Filtered search might not be supported - that's OK for smoke test
            error = result.get("error", "")
            if "unknown" in error.lower() or "not supported" in error.lower():
                return True, "Filtered search not supported (expected for some databases)", result
            return False, f"Error: {error}", result
    except Exception as e:
        return False, f"Exception: {e}", {}


def test_build_index(adapter, collection_name: str) -> Tuple[bool, str, Dict]:
    """Test: Build index (for precondition testing)."""
    try:
        request = {
            "operation": "build_index",
            "params": {
                "collection_name": collection_name,
                "index_type": "IVF_FLAT"
            }
        }
        result = adapter.execute(request)

        if result.get("status") == "success":
            return True, "Index built successfully", result
        else:
            return False, f"Error: {result.get('error')}", result
    except Exception as e:
        return False, f"Exception: {e}", {}


def test_load_index(adapter, collection_name: str) -> Tuple[bool, str, Dict]:
    """Test: Load index (for precondition testing)."""
    try:
        request = {
            "operation": "load_index",
            "params": {
                "collection_name": collection_name
            }
        }
        result = adapter.execute(request)

        if result.get("status") == "success":
            return True, "Index loaded successfully", result
        else:
            return False, f"Error: {result.get('error')}", result
    except Exception as e:
        return False, f"Exception: {e}", {}


def test_cleanup(adapter, collection_name: str) -> Tuple[bool, str, Dict]:
    """Test 6: Cleanup (drop collection)."""
    try:
        request = {
            "operation": "drop_collection",
            "params": {
                "collection_name": collection_name
            }
        }
        result = adapter.execute(request)

        if result.get("status") == "success":
            return True, "Collection dropped", result
        else:
            return False, f"Error: {result.get('error')}", result
    except Exception as e:
        return False, f"Exception: {e}", {}


def main():
    parser = argparse.ArgumentParser(description="Smoke test for real seekdb connection")
    parser.add_argument(
        "--api-endpoint",
        default=os.getenv("SEEKDB_API_ENDPOINT", "http://localhost:8080"),
        help="seekdb API endpoint"
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("SEEKDB_API_KEY", ""),
        help="seekdb API key"
    )
    parser.add_argument(
        "--test-collection",
        default="smoke_test_collection",
        help="Test collection name (will be created and dropped)"
    )
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Skip cleanup (keep test collection for debugging)"
    )

    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  seekdb Smoke Test")
    print("=" * 60)
    print()
    print(f"API Endpoint: {args.api_endpoint}")
    print(f"Test Collection: {args.test_collection}")
    print(f"Skip Cleanup: {args.skip_cleanup}")

    # Import adapter
    try:
        from adapters.seekdb_adapter import SeekDBAdapter
    except ImportError as e:
        print(f"ERROR: Cannot import SeekDBAdapter: {e}")
        sys.exit(1)

    # Initialize adapter
    try:
        adapter = SeekDBAdapter(
            api_endpoint=args.api_endpoint,
            api_key=args.api_key,
            collection=args.test_collection
        )
    except Exception as e:
        print(f"ERROR: Failed to initialize adapter: {e}")
        sys.exit(1)

    # Run tests
    results = []

    # Test 1: Health check
    print_section("Test 1: Health Check / Connection")
    success, details = test_health_check(adapter)
    print_result("Health check", success, details)
    results.append(("health_check", success, details))

    if not success:
        print()
        print("ERROR: Cannot proceed without successful connection")
        print("Please verify:")
        print(f"  - API endpoint is correct: {args.api_endpoint}")
        print(f"  - API key is valid: {'(set)' if args.api_key else '(not set)'}")
        print(f"  - seekdb instance is running and accessible")
        sys.exit(1)

    # Test 2: Create collection
    print_section("Test 2: Create Collection")
    success, details, _ = test_create_collection(adapter, args.test_collection)
    print_result("Create collection", success, details)
    results.append(("create_collection", success, details))

    if not success:
        print()
        print("ERROR: Cannot proceed without creating collection")
        sys.exit(1)

    # Test 3: Insert vectors
    print_section("Test 3: Insert Vectors")
    success, details, insert_result = test_insert(adapter, args.test_collection)
    print_result("Insert vectors", success, details)
    results.append(("insert", success, details))

    # Test 4: Basic search
    print_section("Test 4: Basic Vector Search")
    success, details, search_result = test_search(adapter, args.test_collection)
    print_result("Basic search", success, details)
    if success:
        # Show sample results
        data = search_result.get("data", [])
        if data:
            print(f"       Sample results:")
            for i, item in enumerate(data[:3]):
                print(f"         [{i}] id={item.get('id')}, score={item.get('score'):.4f}")
    results.append(("search", success, details))

    # Test 5: Filtered search
    print_section("Test 5: Filtered Search")
    success, details, _ = test_filtered_search(adapter, args.test_collection)
    print_result("Filtered search", success, details)
    results.append(("filtered_search", success, details))

    # Test: Build index (for precondition)
    print_section("Test: Build Index")
    success, details, _ = test_build_index(adapter, args.test_collection)
    print_result("Build index", success, details)
    results.append(("build_index", success, details))

    # Test: Load index (for precondition)
    print_section("Test: Load Index")
    success, details, _ = test_load_index(adapter, args.test_collection)
    print_result("Load index", success, details)
    results.append(("load_index", success, details))

    # Test 6: Cleanup
    if not args.skip_cleanup:
        print_section("Test 6: Cleanup")
        success, details, _ = test_cleanup(adapter, args.test_collection)
        print_result("Drop collection", success, details)
        results.append(("cleanup", success, details))
    else:
        print_section("Test 6: Cleanup")
        print("SKIP: --skip-cleanup flag set")
        print(f"Test collection '{args.test_collection}' left for debugging")

    # Summary
    print_section("Summary")
    passed = sum(1 for _, s, _ in results if s)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    print()

    for test_name, success, details in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {test_name}")

    print()
    if passed == total:
        print("[OK] All smoke tests passed!")
        print("-> Ready to proceed to Step 2: First real S1 campaign run")
        return 0
    else:
        print("[FAIL] Some smoke tests failed")
        print("-> Please review errors and fix before running campaign")
        return 1


if __name__ == "__main__":
    sys.exit(main())
