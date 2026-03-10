#!/usr/bin/env python3
"""
Qdrant Smoke Test - Real Environment Validation

Validates core Qdrant operations required for R4:
1. create_collection
2. upsert
3. search
4. delete (by ID)
5. delete_collection

This is NOT the full R4 framework.
It is only a real-environment smoke validation.

Usage:
    python scripts/smoke_test_qdrant.py
    python scripts/smoke_test_qdrant.py --url http://localhost:6333
"""

import sys
import argparse
from typing import List, Tuple

try:
    from qdrant_client import QdrantClient, models
    from qdrant_client.http.exceptions import UnexpectedResponse
except ImportError:
    print("ERROR: qdrant-client not installed")
    print("Install with: pip install qdrant-client")
    sys.exit(1)


# Configuration
COLLECTION_NAME = "test_smoke_r4"
VECTOR_DIM = 128
VECTOR_SIZE = 128


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}\n")


def print_step(step_num: int, total: int, operation: str, status: str, details: str = ""):
    """Print a test step result."""
    status_symbol = "[OK]" if status == "OK" else "[FAIL]"
    print(f"[{step_num}/{total}] {operation}... {status_symbol}")
    if details:
        print(f"         {details}")


class QdrantSmokeTest:
    """Smoke test runner for Qdrant operations."""

    def __init__(self, url: str, timeout: float = 30.0):
        self.url = url
        self.timeout = timeout
        self.client = None
        self.test_results: List[Tuple[str, bool, str]] = []

    def connect(self) -> bool:
        """Connect to Qdrant and verify health."""
        try:
            self.client = QdrantClient(url=self.url, timeout=self.timeout)

            # Verify connection by getting collections
            collections = self.client.get_collections()
            print(f"Connected to Qdrant at {self.url}")
            print(f"Current collections: {len(collections.collections)}")
            return True
        except Exception as e:
            print(f"Failed to connect to Qdrant: {e}")
            return False

    def cleanup_existing_collection(self) -> bool:
        """Remove existing test collection if present."""
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if COLLECTION_NAME in collection_names:
                print(f"Found existing collection '{COLLECTION_NAME}', removing...")
                self.client.delete_collection(collection_name=COLLECTION_NAME)
                print(f"Existing collection '{COLLECTION_NAME}' removed")

            return True
        except Exception as e:
            print(f"Warning: Could not cleanup existing collection: {e}")
            return False

    def test_create_collection(self) -> bool:
        """Test 1: Create collection."""
        try:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=VECTOR_DIM,
                    distance=models.Distance.COSINE
                )
            )

            # Verify collection exists
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if COLLECTION_NAME in collection_names:
                self.test_results.append(("create_collection", True, ""))
                return True
            else:
                self.test_results.append(("create_collection", False, "Collection not found after creation"))
                return False

        except Exception as e:
            self.test_results.append(("create_collection", False, str(e)))
            return False

    def test_upsert(self) -> bool:
        """Test 2: Upsert points."""
        try:
            # Create test points
            points = [
                models.PointStruct(
                    id=1,
                    vector=[0.1] * VECTOR_DIM,
                    payload={"color": "red", "label": "A"}
                ),
                models.PointStruct(
                    id=2,
                    vector=[0.9] * VECTOR_DIM,
                    payload={"color": "blue", "label": "B"}
                ),
            ]

            operation_info = self.client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )

            self.test_results.append(("upsert", True, f"inserted {len(points)} points"))
            return True

        except Exception as e:
            self.test_results.append(("upsert", False, str(e)))
            return False

    def test_search(self) -> bool:
        """Test 3: Search vectors."""
        try:
            # Search for vectors similar to [0.1, 0.1, ...]
            # Should match point ID=1 (red) most closely
            results = self.client.search(
                collection_name=COLLECTION_NAME,
                query_vector=[0.1] * VECTOR_DIM,
                limit=5
            )

            if len(results) == 0:
                self.test_results.append(("search", False, "No results returned"))
                return False

            # Check that we got expected results
            if len(results) >= 2:
                top_id = results[0].id
                top_score = results[0].score

                self.test_results.append((
                    "search",
                    True,
                    f"found {len(results)} results, top match: ID={top_id}, score={top_score:.4f}"
                ))
                return True
            else:
                self.test_results.append(("search", False, f"Expected 2 results, got {len(results)}"))
                return False

        except Exception as e:
            self.test_results.append(("search", False, str(e)))
            return False

    def test_delete(self) -> bool:
        """Test 4: Delete point by ID."""
        try:
            # Delete point ID=1
            operation_info = self.client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=models.PointIdsList(points=[1])
            )

            # Verify deletion by searching
            results = self.client.search(
                collection_name=COLLECTION_NAME,
                query_vector=[0.1] * VECTOR_DIM,
                limit=5
            )

            remaining_ids = [r.id for r in results]

            if 1 not in remaining_ids:
                self.test_results.append((
                    "delete",
                    True,
                    f"deleted point ID=1, {len(results)} points remaining"
                ))
                return True
            else:
                self.test_results.append(("delete", False, "Point ID=1 still found after deletion"))
                return False

        except Exception as e:
            self.test_results.append(("delete", False, str(e)))
            return False

    def test_verify_deletion(self) -> bool:
        """Test 5: Verify deleted entity not in search results."""
        try:
            # Search again - should only find point ID=2
            results = self.client.search(
                collection_name=COLLECTION_NAME,
                query_vector=[0.1] * VECTOR_DIM,
                limit=5
            )

            remaining_ids = [r.id for r in results]

            # Point ID=1 should NOT be in results
            if 1 in remaining_ids:
                self.test_results.append((
                    "verify_deletion",
                    False,
                    f"Deleted point ID=1 still visible in results: {remaining_ids}"
                ))
                return False

            # Should have exactly 1 result (ID=2)
            if len(results) == 1 and results[0].id == 2:
                self.test_results.append((
                    "verify_deletion",
                    True,
                    f"correctly excluded deleted point, {len(results)} result(s) remaining"
                ))
                return True
            else:
                self.test_results.append((
                    "verify_deletion",
                    False,
                    f"Unexpected results: {len(results)} results, IDs: {remaining_ids}"
                ))
                return False

        except Exception as e:
            self.test_results.append(("verify_deletion", False, str(e)))
            return False

    def test_delete_collection(self) -> bool:
        """Test 6: Drop collection."""
        try:
            self.client.delete_collection(collection_name=COLLECTION_NAME)

            # Verify collection is gone
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if COLLECTION_NAME not in collection_names:
                self.test_results.append(("delete_collection", True, "collection removed"))
                return True
            else:
                self.test_results.append(("delete_collection", False, "Collection still exists after deletion"))
                return False

        except Exception as e:
            self.test_results.append(("delete_collection", False, str(e)))
            return False

    def test_post_drop_rejection(self) -> bool:
        """Test 7: Verify operations fail after collection drop."""
        try:
            # Try to search on deleted collection - should fail
            try:
                results = self.client.search(
                    collection_name=COLLECTION_NAME,
                    query_vector=[0.1] * VECTOR_DIM,
                    limit=5
                )
                # If we get here, search succeeded (BAD)
                self.test_results.append((
                    "post_drop_rejection",
                    False,
                    "Search succeeded on dropped collection (should fail)"
                ))
                return False
            except Exception:
                # Expected - search should fail
                self.test_results.append((
                    "post_drop_rejection",
                    True,
                    "correctly rejects operations on dropped collection"
                ))
                return True

        except Exception as e:
            self.test_results.append(("post_drop_rejection", False, str(e)))
            return False

    def run_all_tests(self) -> bool:
        """Run all smoke tests."""
        total_steps = 7

        print_header("Qdrant Smoke Test - R4.0")
        print(f"Target: {self.url}")
        print(f"Test Collection: {COLLECTION_NAME}")
        print(f"Vector Dimension: {VECTOR_DIM}")

        # Step 1: Connect
        print()
        if not self.connect():
            print_step(1, total_steps, "Connection", "FAILED", "Could not connect to Qdrant")
            print("\n❌ Smoke test FAILED - Cannot connect to Qdrant")
            print("\nTroubleshooting:")
            print("1. Ensure Qdrant is running: docker ps | grep qdrant")
            print("2. Start Qdrant: docker run -d -p 6333:6333 qdrant/qdrant")
            print("3. Check health: curl http://localhost:6333/")
            return False

        print_step(1, total_steps, "Connection", "OK", f"Connected to {self.url}")

        # Cleanup any existing test collection
        self.cleanup_existing_collection()

        # Step 2: Create collection
        print()
        if self.test_create_collection():
            print_step(2, total_steps, "Create collection", "OK", f"Created '{COLLECTION_NAME}'")
        else:
            print_step(2, total_steps, "Create collection", "FAILED", self.test_results[-1][2])
            return False

        # Step 3: Upsert points
        print()
        if self.test_upsert():
            _, _, details = self.test_results[-1]
            print_step(3, total_steps, "Upsert points", "OK", details)
        else:
            print_step(3, total_steps, "Upsert points", "FAILED", self.test_results[-1][2])
            return False

        # Step 4: Search
        print()
        if self.test_search():
            _, _, details = self.test_results[-1]
            print_step(4, total_steps, "Search", "OK", details)
        else:
            print_step(4, total_steps, "Search", "FAILED", self.test_results[-1][2])
            return False

        # Step 5: Delete
        print()
        if self.test_delete():
            _, _, details = self.test_results[-1]
            print_step(5, total_steps, "Delete point", "OK", details)
        else:
            print_step(5, total_steps, "Delete point", "FAILED", self.test_results[-1][2])
            return False

        # Step 6: Verify deletion
        print()
        if self.test_verify_deletion():
            _, _, details = self.test_results[-1]
            print_step(6, total_steps, "Verify deletion", "OK", details)
        else:
            print_step(6, total_steps, "Verify deletion", "FAILED", self.test_results[-1][2])
            return False

        # Step 7: Delete collection
        print()
        if self.test_delete_collection():
            print_step(7, total_steps, "Drop collection", "OK", "Collection removed")
        else:
            print_step(7, total_steps, "Drop collection", "FAILED", self.test_results[-1][2])
            return False

        # Step 8: Post-drop rejection (bonus test)
        print()
        if self.test_post_drop_rejection():
            print_step(8, total_steps, "Post-drop rejection", "OK", "Operations correctly rejected")
        else:
            print_step(8, total_steps, "Post-drop rejection", "FAILED", self.test_results[-1][2])
            # This is not a hard failure for the smoke test, but worth noting

        return True

    def print_summary(self):
        """Print test summary."""
        print_header("Test Summary")

        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)

        for operation, success, details in self.test_results:
            status = "[PASS]" if success else "[FAIL]"
            print(f"{status}: {operation}")
            if details and not success:
                print(f"       {details}")

        print()
        print(f"Total: {passed}/{total} tests passed")

        if passed == total:
            print("\n[SUCCESS] All smoke tests PASSED")
            print("\nQdrant is ready for R4 implementation.")
            return 0
        else:
            print(f"\n[FAILURE] {total - passed} test(s) FAILED")
            print("\nQdrant is NOT ready for R4 implementation.")
            print("Please troubleshoot and re-run the smoke test.")
            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Qdrant smoke test - validate core operations for R4"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:6333",
        help="Qdrant URL (default: http://localhost:6333)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Connection timeout in seconds (default: 30.0)"
    )

    args = parser.parse_args()

    # Run smoke test
    test = QdrantSmokeTest(url=args.url, timeout=args.timeout)
    success = test.run_all_tests()

    # Print summary and exit
    return test.print_summary()


if __name__ == "__main__":
    sys.exit(main())
