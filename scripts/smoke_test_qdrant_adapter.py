#!/usr/bin/env python3
"""
Qdrant Adapter Smoke Test

Validates that the Qdrant adapter:
1. Implements all 7 operations correctly
2. Produces normalized outputs compatible with the framework
3. Handles no-op methods (build_index, load) correctly

Usage:
    python scripts/smoke_test_qdrant_adapter.py
"""

import sys
import os
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from adapters.qdrant_adapter import QdrantAdapter


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}\n")


def print_result(test_name: str, success: bool, details: str = ""):
    """Print test result."""
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status}: {test_name}")
    if details:
        print(f"       {details}")


class AdapterSmokeTest:
    """Smoke test runner for Qdrant adapter."""

    def __init__(self):
        self.adapter = None
        self.test_results = []
        self.collection_name = "smoke_test_adapter"

    def setup(self):
        """Initialize adapter."""
        try:
            config = {
                "url": "http://localhost:6333",
                "timeout": 30.0
            }
            self.adapter = QdrantAdapter(config)

            # Health check
            if not self.adapter.health_check():
                print("[FAIL]: Cannot connect to Qdrant")
                print("       Start Qdrant: docker run -d -p 6333:6333 qdrant/qdrant")
                return False

            print(f"[PASS]: Connected to Qdrant")
            return True
        except Exception as e:
            print(f"[FAIL]: Adapter initialization failed: {e}")
            return False

    def cleanup(self):
        """Clean up test collection."""
        try:
            request = {
                "operation": "drop_collection",
                "params": {"collection_name": self.collection_name}
            }
            self.adapter.execute(request)
        except Exception:
            pass

    def test_create_collection(self) -> bool:
        """Test create_collection operation."""
        request = {
            "operation": "create_collection",
            "params": {
                "collection_name": self.collection_name,
                "dimension": 128,
                "metric_type": "COSINE"
            }
        }

        response = self.adapter.execute(request)

        success = (
            response["status"] == "success" and
            "data" in response and
            response["data"]["collection_name"] == self.collection_name
        )

        self.test_results.append(("create_collection", success))
        return success

    def test_insert(self) -> bool:
        """Test insert operation."""
        request = {
            "operation": "insert",
            "params": {
                "collection_name": self.collection_name,
                "vectors": [[0.1] * 128, [0.9] * 128],
                "ids": [1, 2],
                "payload": {"color": "red"}
            }
        }

        response = self.adapter.execute(request)

        success = (
            response["status"] == "success" and
            "data" in response and
            response["data"]["inserted_count"] == 2 and
            response["data"]["ids"] == [1, 2]
        )

        self.test_results.append(("insert", success))
        return success

    def test_insert_auto_id(self) -> bool:
        """Test insert with auto-generated IDs."""
        request = {
            "operation": "insert",
            "params": {
                "collection_name": self.collection_name,
                "vectors": [[0.5] * 128]
            }
        }

        response = self.adapter.execute(request)

        success = (
            response["status"] == "success" and
            "data" in response and
            response["data"]["inserted_count"] == 1 and
            "ids" in response["data"]
        )

        self.test_results.append(("insert_auto_id", success))
        return success

    def test_search(self) -> bool:
        """Test search operation."""
        request = {
            "operation": "search",
            "params": {
                "collection_name": self.collection_name,
                "query_vector": [0.1] * 128,
                "top_k": 5
            }
        }

        response = self.adapter.execute(request)

        success = (
            response["status"] == "success" and
            "data" in response and
            "results" in response["data"] and
            len(response["data"]["results"]) > 0
        )

        self.test_results.append(("search", success))
        return success

    def test_search_normalized_format(self) -> bool:
        """Test that search results are in normalized format."""
        request = {
            "operation": "search",
            "params": {
                "collection_name": self.collection_name,
                "query_vector": [0.1] * 128,
                "top_k": 5
            }
        }

        response = self.adapter.execute(request)

        if response["status"] != "success":
            self.test_results.append(("search_normalized_format", False))
            return False

        results = response["data"]["results"]
        first_result = results[0]

        success = (
            "id" in first_result and
            "score" in first_result and
            "payload" in first_result
        )

        self.test_results.append(("search_normalized_format", success))
        return success

    def test_delete(self) -> bool:
        """Test delete operation."""
        # First insert a test point
        insert_request = {
            "operation": "insert",
            "params": {
                "collection_name": self.collection_name,
                "vectors": [[0.3] * 128],
                "ids": [999]
            }
        }
        self.adapter.execute(insert_request)

        # Delete the point
        delete_request = {
            "operation": "delete",
            "params": {
                "collection_name": self.collection_name,
                "ids": [999]
            }
        }

        response = self.adapter.execute(delete_request)

        success = (
            response["status"] == "success" and
            "data" in response and
            response["data"]["deleted_count"] == 1
        )

        self.test_results.append(("delete", success))
        return success

    def test_drop_collection(self) -> bool:
        """Test drop_collection operation."""
        request = {
            "operation": "drop_collection",
            "params": {
                "collection_name": self.collection_name
            }
        }

        response = self.adapter.execute(request)

        success = (
            response["status"] == "success" and
            "data" in response and
            response["data"]["deleted"] is True
        )

        self.test_results.append(("drop_collection", success))
        return success

    def test_build_index_noop(self) -> bool:
        """Test that build_index is a no-op."""
        # Create collection first
        create_request = {
            "operation": "create_collection",
            "params": {
                "collection_name": self.collection_name,
                "dimension": 128
            }
        }
        self.adapter.execute(create_request)

        # Call build_index
        request = {
            "operation": "build_index",
            "params": {
                "collection_name": self.collection_name
            }
        }

        response = self.adapter.execute(request)

        success = (
            response["status"] == "success" and
            "data" in response and
            response["data"]["operation"] == "no-op" and
            "auto-creates" in response["data"]["note"]
        )

        self.test_results.append(("build_index_noop", success))
        return success

    def test_load_noop(self) -> bool:
        """Test that load is a no-op."""
        request = {
            "operation": "load",
            "params": {
                "collection_name": self.collection_name
            }
        }

        response = self.adapter.execute(request)

        success = (
            response["status"] == "success" and
            "data" in response and
            response["data"]["operation"] == "no-op" and
            "auto-loads" in response["data"]["note"]
        )

        self.test_results.append(("load_noop", success))
        return success

    def test_unknown_operation(self) -> bool:
        """Test unknown operation returns error."""
        request = {
            "operation": "unknown_operation",
            "params": {}
        }

        response = self.adapter.execute(request)

        success = (
            response["status"] == "error" and
            "error" in response
        )

        self.test_results.append(("unknown_operation_error", success))
        return success

    def test_search_after_drop(self) -> bool:
        """Test that search fails after drop (validates Property 1)."""
        # Create collection
        create_request = {
            "operation": "create_collection",
            "params": {
                "collection_name": self.collection_name,
                "dimension": 128
            }
        }
        self.adapter.execute(create_request)

        # Insert data
        insert_request = {
            "operation": "insert",
            "params": {
                "collection_name": self.collection_name,
                "vectors": [[0.1] * 128],
                "ids": [1]
            }
        }
        self.adapter.execute(insert_request)

        # Drop collection
        drop_request = {
            "operation": "drop_collection",
            "params": {"collection_name": self.collection_name}
        }
        self.adapter.execute(drop_request)

        # Search should fail
        search_request = {
            "operation": "search",
            "params": {
                "collection_name": self.collection_name,
                "query_vector": [0.1] * 128,
                "top_k": 5
            }
        }

        response = self.adapter.execute(search_request)

        success = (
            response["status"] == "error" and
            "error" in response
        )

        self.test_results.append(("search_after_drop_fails", success))
        return success

    def run_all_tests(self):
        """Run all adapter smoke tests."""
        print_header("Qdrant Adapter Smoke Test")

        # Setup
        if not self.setup():
            return False

        # Run tests
        tests = [
            ("create_collection", self.test_create_collection),
            ("insert", self.test_insert),
            ("insert_auto_id", self.test_insert_auto_id),
            ("search", self.test_search),
            ("search_normalized_format", self.test_search_normalized_format),
            ("delete", self.test_delete),
            ("drop_collection", self.test_drop_collection),
            ("build_index_noop", self.test_build_index_noop),
            ("load_noop", self.test_load_noop),
            ("unknown_operation_error", self.test_unknown_operation),
            ("search_after_drop_fails", self.test_search_after_drop),
        ]

        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                print(f"[ERROR]: {test_name} raised exception: {e}")
                self.test_results.append((test_name, False))

        # Cleanup
        self.cleanup()

        return True

    def print_summary(self):
        """Print test summary."""
        print_header("Adapter Smoke Test Summary")

        passed = sum(1 for _, success in self.test_results if success)
        total = len(self.test_results)

        for test_name, success in self.test_results:
            print_result(test_name, success)

        print(f"\nTotal: {passed}/{total} tests passed")

        if passed == total:
            print("\n[SUCCESS]: All adapter smoke tests PASSED")
            print("\nAdapter validation:")
            print("- All 7 operations work through adapter interface")
            print("- Normalized output format is compatible")
            print("- build_index() and load() no-op behavior is clean")
            print("\nAdapter is ready for pilot differential campaign.")
            return 0
        else:
            print(f"\n[FAILURE]: {total - passed} test(s) FAILED")
            print("\nAdapter needs fixes before pilot campaign.")
            return 1


def main():
    """Main entry point."""
    test = AdapterSmokeTest()
    test.run_all_tests()
    return test.print_summary()


if __name__ == "__main__":
    sys.exit(main())
