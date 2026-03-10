"""Smoke test runner for SCH006B-001.

SCH-006b: Filter Semantics Verification
Tests if filter on dynamic scalar fields actually works in Milvus.
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
from casegen.generators.sch006b_001_generator import Sch006b001Generator
from pipeline.oracles.sch006b_001_oracle import Sch006b001Oracle


def create_collection_with_dynamic_schema(adapter: MilvusAdapter, case: Dict) -> Dict:
    """Create collection with dynamic scalar field schema."""
    collection_name = case["collection_name"]
    field_types = case["field_types"]

    # Build schema from field_types
    from pymilvus import FieldSchema, CollectionSchema, DataType, Collection, connections

    fields = []
    for field_def in field_types:
        field_name = field_def["name"]
        field_type = field_def["type"]

        # Map type string to DataType
        type_map = {
            "INT64": DataType.INT64,
            "FLOAT_VECTOR": DataType.FLOAT_VECTOR,
            "VARCHAR": DataType.VARCHAR,
        }

        dtype = type_map.get(field_type, DataType.VARCHAR)

        field_kwargs = {"name": field_name, "dtype": dtype}

        if field_def.get("is_primary"):
            field_kwargs["is_primary"] = True
            field_kwargs["autoID"] = field_def.get("autoID", False)

        if field_type == "FLOAT_VECTOR":
            field_kwargs["dim"] = case["dimension"]

        if field_type == "VARCHAR":
            field_kwargs["max_length"] = field_def.get("params", {}).get("max_length", 256)

        if field_def.get("nullable") is not None:
            # Note: nullable is set via enable_dynamic_field in schema
            pass

        fields.append(FieldSchema(**field_kwargs))

    schema = CollectionSchema(fields, f"SCH006B test collection: {collection_name}")

    # Create collection
    collection = Collection(name=collection_name, schema=schema, using="default")

    return {
        "status": "success",
        "operation": "create_collection",
        "collection_name": collection_name
    }


def insert_entities(adapter: MilvusAdapter, case: Dict) -> Dict:
    """Insert entities with scalar field values."""
    collection_name = case["collection_name"]
    entities = case["insert_data"]["entities"]

    # Prepare data columns (Milvus expects columnar format)
    data_columns = []

    # For each field in schema, create a column with all values
    for field_def in case["field_types"]:
        field_name = field_def["name"]
        field_type = field_def["type"]
        column_data = []
        for entity in entities:
            value = entity.get(field_name)
            # Convert None to empty string for VARCHAR fields
            if value is None and field_type == "VARCHAR":
                value = ""
            column_data.append(value)
        data_columns.append(column_data)

    # Insert using pymilvus directly
    from pymilvus import Collection
    collection = Collection(collection_name, using="default")

    result = collection.insert(data_columns)

    return {
        "status": "success",
        "operation": "insert",
        "insert_count": result.insert_count,
        "entities": entities
    }


def run_baseline_query(adapter: MilvusAdapter, collection_name: str) -> Dict:
    """Query without filter to verify data exists."""
    from pymilvus import Collection

    collection = Collection(collection_name, using="default")

    # Load collection first
    collection.load()

    # Query all entities - empty expression needs limit
    result = collection.query(
        expr="",
        output_fields=["*"],
        limit=1000  # Large limit to get all entities
    )

    return {
        "status": "success",
        "operation": "query",
        "collection_name": collection_name,
        "filter_expression": None,
        "result": {
            "count": len(result),
            "results": result
        }
    }


def run_filter_query(adapter: MilvusAdapter, collection_name: str, filter_expr: str) -> Dict:
    """Query with filter to test filter semantics."""
    from pymilvus import Collection

    collection = Collection(collection_name, using="default")

    # Ensure collection is loaded
    collection.load()

    # Query with filter
    result = collection.query(
        expr=filter_expr,
        output_fields=["*"]
    )

    return {
        "status": "success",
        "operation": "query",
        "collection_name": collection_name,
        "filter_expression": filter_expr,
        "result": {
            "count": len(result),
            "results": result
        }
    }


def execute_case(adapter: MilvusAdapter, case: Dict) -> Dict:
    """Execute a single test case."""
    execution_trace = []
    case_result = {
        "case_id": case["case_id"],
        "contract_id": case["contract_id"],
        "name": case["name"],
        "oracle_expectations": case["oracle_expectations"]
    }

    try:
        # Step 1: Create collection
        print(f"  Creating collection: {case['collection_name']}")
        result = create_collection_with_dynamic_schema(adapter, case)
        execution_trace.append({
            "step": len(execution_trace) + 1,
            "operation": "create_collection",
            "params": {
                "collection_name": case["collection_name"],
                "field_types": case["field_types"]
            },
            "result_status": result.get("status"),
            "result": result
        })

        # Step 2: Insert entities
        print(f"  Inserting {len(case['insert_data']['entities'])} entities")
        result = insert_entities(adapter, case)
        execution_trace.append({
            "step": len(execution_trace) + 1,
            "operation": "insert",
            "params": {
                "collection_name": case["collection_name"],
                "entity_count": len(case["insert_data"]["entities"])
            },
            "result_status": result.get("status"),
            "insert_count": result.get("insert_count"),
            "entities": case["insert_data"]["entities"]
        })

        # Step 3: Flush to ensure data visibility
        print(f"  Flushing data to storage")
        result = adapter.execute({
            "operation": "flush",
            "params": {"collection_name": case["collection_name"]}
        })
        execution_trace.append({
            "step": len(execution_trace) + 1,
            "operation": "flush",
            "params": {"collection_name": case["collection_name"]},
            "result_status": result.get("status")
        })

        # Wait a moment for flush to complete
        time.sleep(1)

        # Step 3.5: Build index on vector field (required for query)
        print(f"  Building index")
        result = adapter.execute({
            "operation": "build_index",
            "params": {"collection_name": case["collection_name"]}
        })
        execution_trace.append({
            "step": len(execution_trace) + 1,
            "operation": "build_index",
            "params": {"collection_name": case["collection_name"]},
            "result_status": result.get("status")
        })

        # Step 4: Load collection (required for query)
        print(f"  Loading collection")
        result = adapter.execute({
            "operation": "load",
            "params": {"collection_name": case["collection_name"]}
        })
        execution_trace.append({
            "step": len(execution_trace) + 1,
            "operation": "load",
            "params": {"collection_name": case["collection_name"]},
            "result_status": result.get("status")
        })

        # Step 5: Baseline query (no filter) - verify data exists
        print(f"  Running baseline query (no filter)")
        result = run_baseline_query(adapter, case["collection_name"])
        execution_trace.append({
            "step": len(execution_trace) + 1,
            "operation": "query",
            "params": {"collection_name": case["collection_name"]},
            "result_status": result.get("status"),
            "result": result["result"]
        })

        # Step 6: Filter query - test filter semantics
        filter_expr = case["filter_test"]["filter_expression"]
        print(f"  Running filter query: {filter_expr}")
        result = run_filter_query(adapter, case["collection_name"], filter_expr)
        execution_trace.append({
            "step": len(execution_trace) + 1,
            "operation": "query",
            "params": {
                "collection_name": case["collection_name"],
                "filter_expression": filter_expr
            },
            "result_status": result.get("status"),
            "result": result["result"]
        })

        case_result["execution_trace"] = execution_trace

        # Step 7: Oracle evaluation
        print(f"  Evaluating with oracle...")
        oracle = Sch006b001Oracle()
        oracle_result = oracle.evaluate(case_result, case)
        case_result["oracle"] = oracle_result

        # Print oracle result
        print(f"  Oracle classification: {oracle_result['classification']}")
        print(f"  Oracle reasoning: {oracle_result['reasoning']}")

        # Cleanup: drop collection
        print(f"  Cleaning up: dropping collection")
        adapter.execute({
            "operation": "drop_collection",
            "params": {"collection_name": case["collection_name"]}
        })

    except Exception as e:
        execution_trace.append({
            "step": len(execution_trace) + 1,
            "operation": "error",
            "error": str(e)
        })
        case_result["execution_trace"] = execution_trace
        case_result["oracle"] = {
            "classification": "EXPERIMENT_DESIGN_ISSUE",
            "reasoning": f"Exception during execution: {e}"
        }
        print(f"  ERROR: {e}")

        # Try cleanup
        try:
            adapter.execute({
                "operation": "drop_collection",
                "params": {"collection_name": case["collection_name"]}
            })
        except:
            pass

    return case_result


def main():
    parser = argparse.ArgumentParser(description="Run SCH006B-001 filter semantics tests")
    parser.add_argument("--mode", default="REAL", choices=["MOCK", "REAL"])
    parser.add_argument("--output", "-o", help="Output results JSON path")
    args = parser.parse_args()

    print("SCH006B-001: Filter Semantics Verification")
    print("=" * 50)

    # Skip if MOCK mode
    if args.mode == "MOCK":
        print("MOCK mode - not executing real tests")
        print("Use --mode REAL to run against Milvus")
        return 0

    # Initialize adapter
    print("\nInitializing Milvus adapter...")
    adapter = MilvusAdapter({
        "host": "localhost",
        "port": 19530,
        "alias": "default"
    })
    print("Connected to Milvus")

    # Generate test cases
    print("\nGenerating test cases...")
    generator = Sch006b001Generator({})
    cases = generator.generate()
    print(f"Generated {len(cases)} test cases")

    # Execute cases
    results = []
    for i, case in enumerate(cases, 1):
        print(f"\n--- Case {i}/{len(cases)}: {case['name']} ---")
        result = execute_case(adapter, case)
        results.append(result)

    # Compile report
    run_id = f"sch006b-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    report = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "database": "Milvus v2.6.10",
        "mode": args.mode,
        "campaign": "SCH006B Filter Semantics Verification",
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
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Run ID: {run_id}")
    print(f"Total cases: {len(results)}")
    print("\nClassifications:")
    for cls, count in report["summary"]["by_classification"].items():
        print(f"  {cls}: {count}")

    # Save results
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(f"results/sch006b_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))
    print(f"\nResults saved to: {output_path}")

    return 0


if __name__ == "__main__":
    exit(main())
