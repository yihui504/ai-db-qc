"""Smoke test runner for R6A-001.

R6A-001: Consistency / Visibility Campaign (Round 1 Core)
Tests: CONS-001, CONS-002, CONS-003, CONS-005
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.milvus_adapter import MilvusAdapter
from pymilvus import FieldSchema, CollectionSchema, Collection, DataType, connections


def create_collection_with_index(adapter: MilvusAdapter, case: Dict) -> Dict:
    """Create collection with index."""
    collection_name = case["collection_name"]
    dimension = case["dimension"]

    # Define schema
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension)
    ]
    schema = CollectionSchema(fields, f"R6A test: {collection_name}")

    # Create collection
    collection = Collection(name=collection_name, schema=schema, using="default")

    # Create index (required for search)
    index_params = {"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 128}}
    collection.create_index(field_name="vector", index_params=index_params)

    return {
        "status": "success",
        "operation": "create_collection_with_index",
        "collection_name": collection_name
    }


def insert_data(adapter: MilvusAdapter, collection_name: str, num_entities: int, dimension: int = 128) -> Dict:
    """Insert test data."""
    # Generate test vectors - each entity gets its own vector list
    import random
    random.seed(42)
    vectors = [[random.random() for _ in range(dimension)] for _ in range(num_entities)]

    # Prepare data columns
    ids = list(range(num_entities))

    collection = Collection(collection_name, using="default")
    result = collection.insert([ids, vectors])

    return {
        "status": "success",
        "operation": "insert",
        "insert_count": result.insert_count,
        "num_entities": num_entities
    }


def execute_r6a001_case(adapter: MilvusAdapter, case: Dict) -> Dict:
    """Execute a single R6A-001 test case."""
    execution_trace = []
    case_result = {
        "case_id": case["case_id"],
        "contract_id": case["contract_id"],
        "name": case["name"],
        "oracle_expectations": case.get("oracle_expectations", {})
    }

    try:
        # CONS-001: Insert Return vs Storage Visibility
        if case["case_id"] == "R6A-001":
            # Step 1: Create collection
            result = create_collection_with_index(adapter, case)
            execution_trace.append({"step": 1, "operation": "create_collection", "result_status": "success"})

            # Step 2: Insert
            result = insert_data(adapter, case["collection_name"], case["num_entities"])
            execution_trace.append({"step": 2, "operation": "insert", "result_status": "success", "insert_count": result["insert_count"]})

            # Step 3: Check num_entities pre-flush
            collection = Collection(case["collection_name"], using="default")
            pre_flush_count = collection.num_entities
            execution_trace.append({"step": 3, "operation": "check_num_entities_pre_flush", "num_entities": pre_flush_count})

            # Step 4: Flush
            adapter.execute({"operation": "flush", "params": {"collection_name": case["collection_name"]}})
            time.sleep(0.5)
            execution_trace.append({"step": 4, "operation": "flush", "result_status": "success"})

            # Step 5: Check num_entities post-flush
            post_flush_count = collection.num_entities
            execution_trace.append({"step": 5, "operation": "check_num_entities_post_flush", "num_entities": post_flush_count})

            # Cleanup
            adapter.execute({"operation": "drop_collection", "params": {"collection_name": case["collection_name"]}})

        # CONS-002: Storage vs Search Visibility
        elif case["case_id"] == "R6A-002":
            # Create, insert, flush
            create_collection_with_index(adapter, case)
            execution_trace.append({"step": 1, "operation": "create_collection_with_index", "result_status": "success"})

            result = insert_data(adapter, case["collection_name"], case["num_entities"])
            execution_trace.append({"step": 2, "operation": "insert", "result_status": "success", "insert_count": result["insert_count"]})

            adapter.execute({"operation": "flush", "params": {"collection_name": case["collection_name"]}})
            time.sleep(0.5)
            execution_trace.append({"step": 3, "operation": "flush", "result_status": "success"})

            # Check storage count
            collection = Collection(case["collection_name"], using="default")
            storage_count = collection.num_entities
            execution_trace.append({"step": 4, "operation": "check_storage_count", "num_entities": storage_count})

            # Search without load
            try:
                search_data = [[0.1] * case["dimension"]]
                results = collection.search(data=search_data, anns_field="vector", param={"metric_type": "L2", "params": {"nprobe": 10}}, limit=10)
                search_without_count = len(results[0])
                execution_trace.append({"step": 5, "operation": "search_without_load", "result_status": "success", "result": {"results": results[0], "count": search_without_count}})
            except Exception as e:
                execution_trace.append({"step": 5, "operation": "search_without_load", "result_status": "error", "error": str(e)})

            # Load and search
            collection.load()
            time.sleep(0.5)
            results = collection.search(data=search_data, anns_field="vector", param={"metric_type": "L2", "params": {"nprobe": 10}}, limit=10)
            search_with_count = len(results[0])
            execution_trace.append({"step": 6, "operation": "search_with_load", "result_status": "success", "result": {"results": results[0], "count": search_with_count}})

            # Cleanup
            collection.release()
            adapter.execute({"operation": "drop_collection", "params": {"collection_name": case["collection_name"]}})

        # CONS-003: Load/Release/Reload Gate
        elif case["case_id"] == "R6A-003":
            create_collection_with_index(adapter, case)
            execution_trace.append({"step": 1, "operation": "create_collection_with_index", "result_status": "success"})

            insert_data(adapter, case["collection_name"], case["num_entities"])
            execution_trace.append({"step": 2, "operation": "insert", "result_status": "success"})

            adapter.execute({"operation": "flush", "params": {"collection_name": case["collection_name"]}})
            execution_trace.append({"step": 3, "operation": "flush", "result_status": "success"})

            collection = Collection(case["collection_name"], using="default")
            collection.load()
            execution_trace.append({"step": 4, "operation": "load", "result_status": "success"})

            # Baseline search
            search_data = [[0.1] * case["dimension"]]
            results = collection.search(data=search_data, anns_field="vector", param={"metric_type": "L2", "params": {"nprobe": 10}}, limit=10)
            baseline_count = len(results[0])
            execution_trace.append({"step": 5, "operation": "search_baseline", "result_status": "success", "result": {"results": results[0], "count": baseline_count}})

            # Release
            collection.release()
            execution_trace.append({"step": 6, "operation": "release", "result_status": "success"})

            # Verify unloaded
            from pymilvus import utility
            load_state = utility.load_state(case["collection_name"], using="default")
            execution_trace.append({"step": 7, "operation": "verify_unloaded", "load_state": str(load_state)})

            # Search unloaded (should fail)
            try:
                results = collection.search(data=search_data, anns_field="vector", param={"metric_type": "L2", "params": {"nprobe": 10}}, limit=10)
                execution_trace.append({"step": 8, "operation": "search_unloaded", "result_status": "success", "result": {"results": results[0], "count": len(results[0])}})
            except Exception as e:
                execution_trace.append({"step": 8, "operation": "search_unloaded", "result_status": "error", "error": str(e)})

            # Reload and search
            collection.load()
            time.sleep(0.5)
            results = collection.search(data=search_data, anns_field="vector", param={"metric_type": "L2", "params": {"nprobe": 10}}, limit=10)
            reload_count = len(results[0])
            execution_trace.append({"step": 9, "operation": "reload", "result_status": "success"})
            execution_trace.append({"step": 10, "operation": "search_after_reload", "result_status": "success", "result": {"results": results[0], "count": reload_count}})

            # Cleanup
            collection.release()
            adapter.execute({"operation": "drop_collection", "params": {"collection_name": case["collection_name"]}})

        # CONS-005: Release Preserves Storage Data
        elif case["case_id"] == "R6A-005":
            create_collection_with_index(adapter, case)
            execution_trace.append({"step": 1, "operation": "create_collection_with_index", "result_status": "success"})

            insert_data(adapter, case["collection_name"], case["num_entities"])
            execution_trace.append({"step": 2, "operation": "insert", "result_status": "success"})

            adapter.execute({"operation": "flush", "params": {"collection_name": case["collection_name"]}})
            execution_trace.append({"step": 3, "operation": "flush", "result_status": "success"})

            collection = Collection(case["collection_name"], using="default")
            collection.load()
            execution_trace.append({"step": 4, "operation": "load", "result_status": "success"})

            # Record storage baseline
            baseline_storage = collection.num_entities
            execution_trace.append({"step": 5, "operation": "record_storage_count_baseline", "num_entities": baseline_storage})

            # Search baseline
            search_data = [[0.1] * case["dimension"]]
            results = collection.search(data=search_data, anns_field="vector", param={"metric_type": "L2", "params": {"nprobe": 10}}, limit=10)
            baseline_results = len(results[0])
            execution_trace.append({"step": 6, "operation": "search_baseline", "result_status": "success", "result": {"results": results[0], "count": baseline_results}})

            # Release
            collection.release()
            execution_trace.append({"step": 7, "operation": "release", "result_status": "success"})

            # Check storage after release
            after_release_storage = collection.num_entities
            execution_trace.append({"step": 8, "operation": "check_storage_count_after_release", "num_entities": after_release_storage})

            # Reload and search
            collection.load()
            time.sleep(0.5)
            results = collection.search(data=search_data, anns_field="vector", param={"metric_type": "L2", "params": {"nprobe": 10}}, limit=10)
            reload_results = len(results[0])
            execution_trace.append({"step": 9, "operation": "reload", "result_status": "success"})
            execution_trace.append({"step": 10, "operation": "search_after_reload", "result_status": "success", "result": {"results": results[0], "count": reload_results}})

            # Cleanup
            collection.release()
            adapter.execute({"operation": "drop_collection", "params": {"collection_name": case["collection_name"]}})

        # R6A-004: CONS-004 Insert-Search Timing Window Observation
        elif case["case_id"] == "R6A-004":
            create_collection_with_index(adapter, case)
            execution_trace.append({"step": 1, "operation": "create_collection_with_index", "result_status": "success"})

            collection = Collection(case["collection_name"], using="default")
            collection.load()
            execution_trace.append({"step": 2, "operation": "load", "result_status": "success"})

            # Insert
            insert_data(adapter, case["collection_name"], case["num_entities"])
            execution_trace.append({"step": 3, "operation": "insert", "result_status": "success"})

            search_data = [[0.1] * case["dimension"]]

            # Search t=0 (immediate)
            results = collection.search(data=search_data, anns_field="vector", param={"metric_type": "L2", "params": {"nprobe": 10}}, limit=10)
            t0_count = len(results[0])
            execution_trace.append({"step": 4, "operation": "search_t0_immediate", "result_status": "success", "search_count": t0_count})

            # Wait 1 second
            time.sleep(1.0)

            # Search t=1s (after wait, no flush)
            results = collection.search(data=search_data, anns_field="vector", param={"metric_type": "L2", "params": {"nprobe": 10}}, limit=10)
            t1_count = len(results[0])
            execution_trace.append({"step": 5, "operation": "search_t1_after_wait", "result_status": "success", "search_count": t1_count, "wait_seconds": 1.0})

            # Flush
            adapter.execute({"operation": "flush", "params": {"collection_name": case["collection_name"]}})
            time.sleep(0.5)
            execution_trace.append({"step": 6, "operation": "flush", "result_status": "success"})

            # Search after flush (baseline)
            results = collection.search(data=search_data, anns_field="vector", param={"metric_type": "L2", "params": {"nprobe": 10}}, limit=10)
            flush_count = len(results[0])
            execution_trace.append({"step": 7, "operation": "search_after_flush_baseline", "result_status": "success", "search_count": flush_count})

            # Cleanup
            collection.release()
            adapter.execute({"operation": "drop_collection", "params": {"collection_name": case["collection_name"]}})

        # R6A-006: CONS-006 Repeated Flush Stability
        elif case["case_id"] == "R6A-006":
            create_collection_with_index(adapter, case)
            execution_trace.append({"step": 1, "operation": "create_collection_with_index", "result_status": "success"})

            insert_data(adapter, case["collection_name"], case["num_entities"])
            execution_trace.append({"step": 2, "operation": "insert", "result_status": "success"})

            collection = Collection(case["collection_name"], using="default")

            # First flush
            adapter.execute({"operation": "flush", "params": {"collection_name": case["collection_name"]}})
            time.sleep(0.5)
            execution_trace.append({"step": 3, "operation": "flush_first", "result_status": "success"})

            # Check storage state before second flush
            before_storage = collection.num_entities
            execution_trace.append({"step": 4, "operation": "check_storage_state_before_second", "num_entities": before_storage})

            # Load and check search state before second flush
            collection.load()
            time.sleep(0.5)
            search_data = [[0.1] * case["dimension"]]
            results = collection.search(data=search_data, anns_field="vector", param={"metric_type": "L2", "params": {"nprobe": 10}}, limit=10)
            before_search = len(results[0])
            execution_trace.append({"step": 5, "operation": "check_search_state_before_second", "result_status": "success", "search_count": before_search})

            # Second flush
            adapter.execute({"operation": "flush", "params": {"collection_name": case["collection_name"]}})
            time.sleep(0.5)
            execution_trace.append({"step": 6, "operation": "flush_second", "result_status": "success"})

            # Check storage state after second flush
            after_storage = collection.num_entities
            execution_trace.append({"step": 7, "operation": "check_storage_state_after_second", "num_entities": after_storage})

            # Check search state after second flush
            results = collection.search(data=search_data, anns_field="vector", param={"metric_type": "L2", "params": {"nprobe": 10}}, limit=10)
            after_search = len(results[0])
            execution_trace.append({"step": 8, "operation": "check_search_state_after_second", "result_status": "success", "search_count": after_search})

            # Cleanup
            collection.release()
            adapter.execute({"operation": "drop_collection", "params": {"collection_name": case["collection_name"]}})

        case_result["execution_trace"] = execution_trace

    except Exception as e:
        execution_trace.append({
            "step": len(execution_trace) + 1,
            "operation": "error",
            "error": str(e)
        })
        case_result["execution_trace"] = execution_trace
        case_result["oracle"] = {
            "classification": "INFRA_FAILURE",
            "reasoning": f"Exception: {e}"
        }

        # Try cleanup
        try:
            adapter.execute({"operation": "drop_collection", "params": {"collection_name": case["collection_name"]}})
        except:
            pass

        return case_result

    # Oracle evaluation
    from pipeline.oracles.r6a_001_oracle import R6a001Oracle
    oracle = R6a001Oracle()
    contract = {"contract_id": case["contract_id"], "oracle_strategy": case.get("oracle_strategy", "CONSERVATIVE")}
    oracle_result = oracle.evaluate(case_result, contract)
    case_result["oracle"] = oracle_result

    return case_result


def main():
    parser = argparse.ArgumentParser(description="Run R6A-001 smoke tests")
    parser.add_argument("--mode", default="REAL", choices=["MOCK", "REAL"])
    parser.add_argument("--round", default="round1_core", choices=["round1_core", "round2_extended", "all"])
    parser.add_argument("--output", "-o", help="Output results JSON path")
    args = parser.parse_args()

    # Determine which cases to run
    if args.round == "round1_core":
        round_name = "Round 1 Core"
        test_list = "R6A-001 (CONS-001), R6A-002 (CONS-002), R6A-003 (CONS-003), R6A-005 (CONS-005)"
    elif args.round == "round2_extended":
        round_name = "Round 2 Extended"
        test_list = "R6A-004 (CONS-004), R6A-006 (CONS-006)"
    else:  # all
        round_name = "Round 1 Core + Round 2 Extended"
        test_list = "R6A-001, R6A-002, R6A-003, R6A-004, R6A-005, R6A-006"

    print(f"R6A-001: Consistency / Visibility Campaign ({round_name})")
    print("=" * 60)
    print(f"Tests: {test_list}")
    print()

    if args.mode == "MOCK":
        print("MOCK mode - not executing real tests")
        return 0

    # Initialize adapter
    print("Initializing Milvus adapter...")
    adapter = MilvusAdapter({"host": "localhost", "port": 19530, "alias": "default"})
    print("Connected to Milvus")

    # Generate test cases
    from casegen.generators.r6a_001_generator import R6a001Generator
    generator = R6a001Generator({})

    if args.round == "round1_core":
        cases = generator.generate()
    elif args.round == "round2_extended":
        cases = generator.generate_round2()
    else:  # all
        cases = generator.generate() + generator.generate_round2()

    print(f"Generated {len(cases)} test cases ({round_name})")
    print()

    # Execute cases
    results = []
    for i, case in enumerate(cases, 1):
        print(f"--- Case {i}/{len(cases)}: {case['name']} ({case['contract_id']}) ---")
        result = execute_r6a001_case(adapter, case)
        results.append(result)

        oracle_cls = result.get("oracle", {}).get("classification", "UNKNOWN")
        print(f"  Oracle: {oracle_cls}")
        print()

    # Compile report
    run_id = f"r6a-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    report = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "database": "Milvus v2.6.10",
        "mode": args.mode,
        "campaign": "R6A Consistency / Visibility",
        "round": "round1_core",
        "total_cases": len(results),
        "summary": {
            "total": len(results),
            "by_classification": {}
        },
        "results": results
    }

    # Summary by classification
    for r in results:
        cls = r.get("oracle", {}).get("classification", "UNKNOWN")
        report["summary"]["by_classification"][cls] = \
            report["summary"]["by_classification"].get(cls, 0) + 1

    # Output report
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Run ID: {run_id}")
    print(f"Total cases: {len(results)}")
    print("\nClassifications:")
    for cls, count in report["summary"]["by_classification"].items():
        print(f"  {cls}: {count}")

    # Save results (clean non-serializable objects)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(f"results/r6a_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Clean execution_trace for JSON serialization
    def clean_trace(obj):
        if isinstance(obj, dict):
            return {k: clean_trace(v) for k, v in obj.items() if k != "result"}
        elif isinstance(obj, list):
            return [clean_trace(item) for item in obj]
        else:
            return obj

    cleaned_report = clean_trace(report)
    output_path.write_text(json.dumps(cleaned_report, indent=2))
    print(f"\nResults saved to: {output_path}")

    return 0


if __name__ == "__main__":
    exit(main())
