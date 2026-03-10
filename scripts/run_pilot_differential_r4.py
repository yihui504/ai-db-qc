#!/usr/bin/env python3
"""
R4 Phase 1: Pilot Differential Campaign

Tests 3 semantic properties across Milvus and Qdrant:
- Property 1: Post-Drop Rejection
- Property 3: Delete Idempotency
- Property 7: Non-Existent Delete Tolerance

This is a PILOT campaign only - NOT full R4.

Usage:
    python scripts/run_pilot_differential_r4.py
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from adapters.milvus_adapter import MilvusAdapter
from adapters.qdrant_adapter import QdrantAdapter


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}\n")


class PilotDifferentialRunner:
    """Run pilot differential campaign across Milvus and Qdrant."""

    def __init__(self, results_dir: str):
        self.results_dir = results_dir
        self.milvus = None
        self.qdrant = None
        self.raw_results = {"milvus": {}, "qdrant": {}}
        self.differential_results = []

    def setup_adapters(self):
        """Initialize both adapters."""
        try:
            # Milvus config
            milvus_config = {
                "host": "localhost",
                "port": 19530,
                "alias": "pilot_milvus"
            }
            self.milvus = MilvusAdapter(milvus_config)

            # Qdrant config
            qdrant_config = {
                "url": "http://localhost:6333",
                "timeout": 30.0
            }
            self.qdrant = QdrantAdapter(qdrant_config)

            print("[PASS]: Both adapters initialized")
            return True
        except Exception as e:
            print(f"[FAIL]: Adapter initialization failed: {e}")
            return False

    def execute_sequence(self, adapter, adapter_name: str, sequence: List[Dict]) -> List[Dict]:
        """Execute a sequence of operations on an adapter."""
        results = []
        for step in sequence:
            step_num = step.get("step", len(results) + 1)
            operation = step["operation"]
            params = step.get("params", {})

            request = {"operation": operation, "params": params}
            response = adapter.execute(request)

            results.append({
                "step": step_num,
                "operation": operation,
                "status": response["status"],
                "data": response.get("data", {}),
                "error": response.get("error")
            })

        return results

    def run_pilot_001_post_drop_rejection(self) -> Dict:
        """Property 1: Post-Drop Rejection.

        Oracle Rule 1: Both databases must fail operations on dropped collections.
        """
        print("\n--- Pilot-001: Post-Drop Rejection (Property 1) ---")

        case_id = "pilot_001"
        collection_name_milvus = "test_pilot_001_milvus"
        collection_name_qdrant = "test_pilot_001_qdrant"

        # Sequence: create -> insert -> (build_index, load optional) -> search -> drop -> search
        sequence = [
            {"step": 1, "operation": "create_collection", "params": {
                "collection_name": None,  # Will be set per adapter
                "dimension": 128,
                "metric_type": "COSINE"
            }},
            {"step": 2, "operation": "insert", "params": {
                "collection_name": None,
                "vectors": [[0.1] * 128, [0.9] * 128],
                "ids": [1, 2]
            }},
            {"step": 3, "operation": "build_index", "params": {
                "collection_name": None,
                "field_name": "vector",
                "index_type": "HNSW"
            }},
            {"step": 4, "operation": "load", "params": {
                "collection_name": None
            }},
            {"step": 5, "operation": "search", "params": {
                "collection_name": None,
                "query_vector": [0.1] * 128,
                "top_k": 10
            }},
            {"step": 6, "operation": "drop_collection", "params": {
                "collection_name": None
            }},
            {"step": 7, "operation": "search", "params": {
                "collection_name": None,
                "query_vector": [0.1] * 128,
                "top_k": 10
            }},
        ]

        # Run on Milvus
        print("  Running on Milvus...")
        milvus_sequence = []
        for step in sequence:
            step_copy = step.copy()
            step_copy["params"] = step["params"].copy()
            if step_copy["params"].get("collection_name") is None:
                step_copy["params"]["collection_name"] = collection_name_milvus
            milvus_sequence.append(step_copy)

        milvus_results = self.execute_sequence(self.milvus, "milvus", milvus_sequence)

        # Run on Qdrant
        print("  Running on Qdrant...")
        qdrant_sequence = []
        for step in sequence:
            step_copy = step.copy()
            step_copy["params"] = step["params"].copy()
            if step_copy["params"].get("collection_name") is None:
                step_copy["params"]["collection_name"] = collection_name_qdrant
            qdrant_sequence.append(step_copy)

        qdrant_results = self.execute_sequence(self.qdrant, "qdrant", qdrant_sequence)

        # Classify differential result
        step_7_milvus = milvus_results[6]  # Step 7: search after drop
        step_7_qdrant = qdrant_results[6]

        classification = self._classify_post_drop_rejection(step_7_milvus, step_7_qdrant)

        return {
            "case_id": case_id,
            "property": "Post-Drop Rejection",
            "property_number": 1,
            "oracle_rule": "Rule 1 (Search After Drop)",
            "milvus_results": milvus_results,
            "qdrant_results": qdrant_results,
            "classification": classification,
            "test_step": 7,
            "description": "Both databases must fail search on dropped collection"
        }

    def run_pilot_003_delete_idempotency(self) -> Dict:
        """Property 3: Delete Idempotency.

        Oracle Rule 4: Delete operations should be idempotent.
        """
        print("\n--- Pilot-002: Delete Idempotency (Property 3) ---")

        case_id = "pilot_002"
        collection_name_milvus = "test_pilot_002_milvus"
        collection_name_qdrant = "test_pilot_002_qdrant"

        # Sequence: create -> insert -> build_index -> load -> delete -> delete
        sequence = [
            {"step": 1, "operation": "create_collection", "params": {
                "collection_name": None,
                "dimension": 128,
                "metric_type": "COSINE"
            }},
            {"step": 2, "operation": "insert", "params": {
                "collection_name": None,
                "vectors": [[0.1] * 128],
                "ids": [100]
            }},
            {"step": 3, "operation": "build_index", "params": {
                "collection_name": None,
                "field_name": "vector",
                "index_type": "HNSW"
            }},
            {"step": 4, "operation": "load", "params": {
                "collection_name": None
            }},
            {"step": 5, "operation": "delete", "params": {
                "collection_name": None,
                "ids": [100]
            }},
            {"step": 6, "operation": "delete", "params": {
                "collection_name": None,
                "ids": [100]
            }},
        ]

        # Run on Milvus
        print("  Running on Milvus...")
        milvus_sequence = []
        for step in sequence:
            step_copy = step.copy()
            step_copy["params"] = step["params"].copy()
            if step_copy["params"].get("collection_name") is None:
                step_copy["params"]["collection_name"] = collection_name_milvus
            milvus_sequence.append(step_copy)

        milvus_results = self.execute_sequence(self.milvus, "milvus", milvus_sequence)

        # Run on Qdrant
        print("  Running on Qdrant...")
        qdrant_sequence = []
        for step in sequence:
            step_copy = step.copy()
            step_copy["params"] = step["params"].copy()
            if step_copy["params"].get("collection_name") is None:
                step_copy["params"]["collection_name"] = collection_name_qdrant
            qdrant_sequence.append(step_copy)

        qdrant_results = self.execute_sequence(self.qdrant, "qdrant", qdrant_sequence)

        # Classify differential result
        step_6_milvus = milvus_results[5]  # Step 6: second delete
        step_6_qdrant = qdrant_results[5]

        classification = self._classify_delete_idempotency(step_6_milvus, step_6_qdrant)

        return {
            "case_id": case_id,
            "property": "Delete Idempotency",
            "property_number": 3,
            "oracle_rule": "Rule 4 (Delete Idempotency)",
            "milvus_results": milvus_results,
            "qdrant_results": qdrant_results,
            "classification": classification,
            "test_step": 6,
            "description": "Delete operations should be idempotent"
        }

    def run_pilot_007_nonexistent_delete(self) -> Dict:
        """Property 7: Non-Existent Delete Tolerance.

        Oracle Rule 4: Deleting non-existent ID should be handled gracefully.
        """
        print("\n--- Pilot-003: Non-Existent Delete Tolerance (Property 7) ---")

        case_id = "pilot_003"
        collection_name_milvus = "test_pilot_003_milvus"
        collection_name_qdrant = "test_pilot_003_qdrant"

        # Sequence: create -> delete non-existent ID
        sequence = [
            {"step": 1, "operation": "create_collection", "params": {
                "collection_name": None,
                "dimension": 128,
                "metric_type": "COSINE"
            }},
            {"step": 2, "operation": "delete", "params": {
                "collection_name": None,
                "ids": [999]  # Non-existent ID
            }},
        ]

        # Run on Milvus
        print("  Running on Milvus...")
        milvus_sequence = []
        for step in sequence:
            step_copy = step.copy()
            step_copy["params"] = step["params"].copy()
            if step_copy["params"].get("collection_name") is None:
                step_copy["params"]["collection_name"] = collection_name_milvus
            milvus_sequence.append(step_copy)

        milvus_results = self.execute_sequence(self.milvus, "milvus", milvus_sequence)

        # Run on Qdrant
        print("  Running on Qdrant...")
        qdrant_sequence = []
        for step in sequence:
            step_copy = step.copy()
            step_copy["params"] = step["params"].copy()
            if step_copy["params"].get("collection_name") is None:
                step_copy["params"]["collection_name"] = collection_name_qdrant
            qdrant_sequence.append(step_copy)

        qdrant_results = self.execute_sequence(self.qdrant, "qdrant", qdrant_sequence)

        # Classify differential result
        step_2_milvus = milvus_results[1]  # Step 2: delete non-existent
        step_2_qdrant = qdrant_results[1]

        classification = self._classify_nonexistent_delete(step_2_milvus, step_2_qdrant)

        return {
            "case_id": case_id,
            "property": "Non-Existent Delete Tolerance",
            "property_number": 7,
            "oracle_rule": "Rule 4 (Idempotency Extension)",
            "milvus_results": milvus_results,
            "qdrant_results": qdrant_results,
            "classification": classification,
            "test_step": 2,
            "description": "Deleting non-existent ID should be handled gracefully"
        }

    def _classify_post_drop_rejection(self, milvus_step: Dict, qdrant_step: Dict) -> Dict:
        """Classify Property 1: Post-Drop Rejection."""
        milvus_failed = milvus_step["status"] == "error"
        qdrant_failed = qdrant_step["status"] == "error"

        if milvus_failed and qdrant_failed:
            return {
                "result": "CONSISTENT",
                "reasoning": "Both databases correctly fail search on dropped collection",
                "category": "PASS"
            }
        elif not milvus_failed and not qdrant_failed:
            return {
                "result": "INCONSISTENT",
                "reasoning": "Both databases allow post-drop search (VIOLATION)",
                "category": "BUG"
            }
        else:
            return {
                "result": "INCONSISTENT",
                "reasoning": f"One database allows post-drop search: {'Milvus' if not milvus_failed else 'Qdrant'}",
                "category": "BUG"
            }

    def _classify_delete_idempotency(self, milvus_step: Dict, qdrant_step: Dict) -> Dict:
        """Classify Property 3: Delete Idempotency."""
        milvus_succeeds = milvus_step["status"] == "success"
        qdrant_succeeds = qdrant_step["status"] == "success"

        if milvus_succeeds and qdrant_succeeds:
            return {
                "result": "CONSISTENT",
                "reasoning": "Both databases allow repeated delete (idempotent success)",
                "category": "PASS",
                "idempotency_strategy": "both-succeed"
            }
        elif not milvus_succeeds and not qdrant_succeeds:
            return {
                "result": "CONSISTENT",
                "reasoning": "Both databases reject repeated delete (first-succeeds-rest-fail)",
                "category": "PASS",
                "idempotency_strategy": "first-succeeds-rest-fail"
            }
        else:
            return {
                "result": "ALLOWED_DIFFERENCE",
                "reasoning": f"Different idempotency strategies: Milvus={'succeeds' if milvus_succeeds else 'fails'}, Qdrant={'succeeds' if qdrant_succeeds else 'fails'}",
                "category": "ALLOWED",
                "idempotency_strategy": "different"
            }

    def _classify_nonexistent_delete(self, milvus_step: Dict, qdrant_step: Dict) -> Dict:
        """Classify Property 7: Non-Existent Delete Tolerance."""
        milvus_succeeds = milvus_step["status"] == "success"
        qdrant_succeeds = qdrant_step["status"] == "success"

        if milvus_succeeds and qdrant_succeeds:
            return {
                "result": "CONSISTENT",
                "reasoning": "Both databases silently succeed on non-existent delete",
                "category": "PASS",
                "strategy": "silent-success"
            }
        elif not milvus_succeeds and not qdrant_succeeds:
            return {
                "result": "CONSISTENT",
                "reasoning": "Both databases fail with 'not found' error",
                "category": "PASS",
                "strategy": "error-on-not-found"
            }
        else:
            return {
                "result": "ALLOWED_DIFFERENCE",
                "reasoning": f"Different strategies: Milvus={'succeeds' if milvus_succeeds else 'fails'}, Qdrant={'succeeds' if qdrant_succeeds else 'fails'}",
                "category": "ALLOWED",
                "strategy": "different"
            }

    def save_raw_results(self):
        """Save raw results per database."""
        raw_dir = os.path.join(self.results_dir, "raw")
        os.makedirs(raw_dir, exist_ok=True)

        for case in self.differential_results:
            case_id = case["case_id"]

            # Save Milvus results
            milvus_file = os.path.join(raw_dir, f"{case_id}_milvus.json")
            with open(milvus_file, 'w') as f:
                json.dump({
                    "database": "milvus",
                    "case_id": case_id,
                    "property": case["property"],
                    "property_number": case["property_number"],
                    "steps": case["milvus_results"]
                }, f, indent=2)

            # Save Qdrant results
            qdrant_file = os.path.join(raw_dir, f"{case_id}_qdrant.json")
            with open(qdrant_file, 'w') as f:
                json.dump({
                    "database": "qdrant",
                    "case_id": case_id,
                    "property": case["property"],
                    "property_number": case["property_number"],
                    "steps": case["qdrant_results"]
                }, f, indent=2)

        print(f"\n[INFO]: Raw results saved to {raw_dir}")

    def save_differential_results(self):
        """Save differential classification results."""
        diff_dir = os.path.join(self.results_dir, "differential")
        os.makedirs(diff_dir, exist_ok=True)

        for case in self.differential_results:
            case_id = case["case_id"]
            file_path = os.path.join(diff_dir, f"{case_id}_classification.json")

            classification_data = {
                "case_id": case_id,
                "property": case["property"],
                "property_number": case["property_number"],
                "oracle_rule": case["oracle_rule"],
                "description": case["description"],
                "classification": case["classification"],
                "test_step": case["test_step"]
            }

            with open(file_path, 'w') as f:
                json.dump(classification_data, f, indent=2)

        print(f"[INFO]: Differential classifications saved to {diff_dir}")

    def run_pilot_campaign(self):
        """Run the full pilot differential campaign."""
        print_header("R4 Phase 1: Pilot Differential Campaign")
        print("Testing 3 properties across Milvus and Qdrant")
        print("Properties:")
        print("  1. Post-Drop Rejection")
        print("  3. Delete Idempotency")
        print("  7. Non-Existent Delete Tolerance")

        # Setup
        if not self.setup_adapters():
            return 1

        # Run test cases
        print("\n" + "="*60)
        print(" EXECUTING PILOT TEST CASES")
        print("="*60)

        self.differential_results.append(self.run_pilot_001_post_drop_rejection())
        self.differential_results.append(self.run_pilot_003_delete_idempotency())
        self.differential_results.append(self.run_pilot_007_nonexistent_delete())

        # Save results
        self.save_raw_results()
        self.save_differential_results()

        return 0

    def print_summary(self):
        """Print pilot execution summary."""
        print_header("Pilot Execution Summary")

        for case in self.differential_results:
            print(f"\n{case['case_id']}: {case['property']}")
            print(f"  Oracle Rule: {case['oracle_rule']}")
            print(f"  Classification: {case['classification']['result']}")
            print(f"  Category: {case['classification']['category']}")
            print(f"  Reasoning: {case['classification']['reasoning']}")

        # Count categories
        categories = [c["classification"]["category"] for c in self.differential_results]
        pass_count = categories.count("PASS")
        allowed_count = categories.count("ALLOWED")
        bug_count = categories.count("BUG")

        print(f"\n{'='*60}")
        print(f" PILOT RESULTS SUMMARY")
        print(f"{'='*60}")
        print(f"Total Cases: {len(self.differential_results)}")
        print(f"  PASS (CONSISTENT): {pass_count}")
        print(f"  ALLOWED DIFFERENCE: {allowed_count}")
        print(f"  BUG (INCONSISTENT): {bug_count}")

        return {
            "total": len(self.differential_results),
            "pass": pass_count,
            "allowed": allowed_count,
            "bug": bug_count
        }


def main():
    """Main entry point."""
    # Create results directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    results_dir = f"results/r4-pilot-{timestamp}"
    os.makedirs(results_dir, exist_ok=True)

    # Run pilot campaign
    runner = PilotDifferentialRunner(results_dir)
    exit_code = runner.run_pilot_campaign()

    if exit_code == 0:
        runner.print_summary()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
