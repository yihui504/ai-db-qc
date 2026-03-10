"""R3 Sequence/State-Based Campaign Execution Script.

This script executes sequence-based tests for R3, which test state transitions,
idempotency, and data visibility across multi-operation sequences.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from adapters.milvus_adapter import MilvusAdapter
    from adapters.mock import MockAdapter
    from pymilvus import connections, utility
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed")
    sys.exit(1)


class SequenceStep:
    """Represents a single step in a sequence test."""

    def __init__(self, step_data: Dict[str, Any], substitutions: Dict[str, str]):
        self.step_number = step_data.get("step", 0)
        self.operation = step_data.get("operation", "")
        self.params = self._substitute_params(step_data.get("param_template", {}), substitutions)
        self.expected_behavior = step_data.get("expected_behavior", "")

    def _substitute_params(self, params: Dict[str, Any], substitutions: Dict[str, str]) -> Dict[str, Any]:
        """Apply substitutions to parameter values."""
        result = {}
        for key, value in params.items():
            if isinstance(value, str):
                for sub_key, sub_value in substitutions.items():
                    value = value.replace(f"{{{sub_key}}}", sub_value)
                result[key] = value
            else:
                result[key] = value
        return result


class SequenceCase:
    """Represents a sequence-based test case."""

    def __init__(self, template: Dict[str, Any], substitutions: Dict[str, str]):
        self.template_id = template.get("template_id", "")
        self.name = template.get("name", "")
        self.type = template.get("type", "primary")
        self.state_property = template.get("state_property", "")
        self.rationale = template.get("rationale", "")
        self.sequence = [
            SequenceStep(step, substitutions)
            for step in template.get("sequence", [])
        ]


class SequenceExecutor:
    """Executes sequence-based tests against Milvus."""

    def __init__(self, adapter, adapter_type: str = "milvus"):
        self.adapter = adapter
        self.adapter_type = adapter_type
        self.results = []

    def execute_sequence(self, case: SequenceCase, run_id: str) -> Dict[str, Any]:
        """Execute a sequence case and return results."""
        print(f"  Executing: {case.template_id} - {case.name}")

        case_result = {
            "template_id": case.template_id,
            "name": case.name,
            "type": case.type,
            "state_property": case.state_property,
            "rationale": case.rationale,
            "steps_executed": [],
            "overall_status": "unknown",
            "findings": [],
            "run_id": run_id
        }

        collection_name = None
        all_success = True

        for step in case.sequence:
            step_result = {
                "step": step.step_number,
                "operation": step.operation,
                "params": step.params,
                "expected_behavior": step.expected_behavior,
                "status": "unknown",
                "error": None,
                "data": None,
                "timestamp": datetime.now().isoformat()
            }

            try:
                # Track collection name for cleanup
                if step.operation == "create_collection":
                    collection_name = step.params.get("collection_name")

                # Execute operation
                request = {
                    "operation": step.operation,
                    "params": step.params
                }

                response = self.adapter.execute(request)

                step_result["status"] = response.get("status", "unknown")
                step_result["data"] = response.get("data", [])

                if response.get("status") == "error":
                    step_result["error"] = response.get("error", "")
                    all_success = False

                # Check if behavior matches expectation
                if step.expected_behavior:
                    step_result["behavior_check"] = self._check_expected_behavior(
                        response, step.expected_behavior
                    )

            except Exception as e:
                step_result["status"] = "error"
                step_result["error"] = str(e)
                all_success = False

            case_result["steps_executed"].append(step_result)

        case_result["overall_status"] = "success" if all_success else "partial_failure" if any(
            s["status"] == "error" for s in case_result["steps_executed"][:-1]
        ) else "completed"

        # Cleanup if collection exists
        if collection_name:
            try:
                self.adapter.execute({
                    "operation": "drop_collection",
                    "params": {"collection_name": collection_name}
                })
            except Exception:
                pass

        return case_result

    def _check_expected_behavior(self, response: Dict, expected: str) -> Dict[str, Any]:
        """Check if response matches expected behavior."""
        return {
            "expected": expected,
            "actual_status": response.get("status"),
            "matches": None  # Will be filled during post-run review
        }


def load_sequence_templates(template_file: str) -> List[Dict[str, Any]]:
    """Load sequence test templates from YAML file."""
    import yaml

    with open(template_file, 'r') as f:
        data = yaml.safe_load(f)

    return data.get("templates", [])


def create_substitutions() -> Dict[str, str]:
    """Create standard substitutions for test data."""
    import random

    return {
        "dimension": "128",
        "metric_type": "L2",
        "index_type": "IVF_FLAT",
        "collection": "test_collection",
        # 128-dimensional vectors
        "vectors_128": json.dumps([
            [0.1, 0.2] * 64,
            [0.3, 0.4] * 64,
            [0.5, 0.6] * 64
        ]),
        # Multiple vectors for multi-delete test
        "vectors_multi": json.dumps([
            [0.1, 0.2] * 64,
            [0.3, 0.4] * 64,
            [0.5, 0.6] * 64
        ]),
        # Query vector (128-dim)
        "query_vector_128": json.dumps([0.1, 0.2] * 64),
    }


def post_run_review(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Perform post-run review and classification of results."""
    review = {
        "cases_reviewed": 0,
        "classifications": {
            "issue_ready": [],
            "observation": [],
            "calibration": [],
            "exploratory": []
        },
        "minimum_success_met": False,
        "findings": []
    }

    primary_cases_completed = 0
    issue_ready_count = 0

    for case_result in results:
        review["cases_reviewed"] += 1

        classification = {
            "template_id": case_result["template_id"],
            "type": case_result["type"],
            "state_property": case_result["state_property"],
            "validly_exercised": False,
            "classification": "unknown",
            "reasoning": ""
        }

        # Check if case was validly exercised
        steps_executed = len(case_result["steps_executed"])
        if steps_executed > 0:
            classification["validly_exercised"] = True

            # Analyze based on case type
            if case_result["type"] == "calibration":
                classification["classification"] = "calibration"
                classification["reasoning"] = "Calibration case - validates known-good behavior"
                review["classifications"]["calibration"].append(classification)

            elif case_result["type"] == "exploratory":
                classification["classification"] = "exploratory"
                classification["reasoning"] = "Exploratory case - documents edge case behavior"
                review["classifications"]["exploratory"].append(classification)

            elif case_result["type"] == "primary":
                primary_cases_completed += 1

                # Analyze primary cases for potential issues
                has_anomaly = False
                anomaly_reasons = []

                for step in case_result["steps_executed"]:
                    # Check for unexpected behaviors
                    if "behavior_check" in step:
                        expected = step["behavior_check"].get("expected", "")
                        actual = step["behavior_check"].get("actual_status", "")

                        # Look for state inconsistencies
                        if "idempotent" in expected.lower() and step.get("status") == "error":
                            has_anomaly = True
                            anomaly_reasons.append(f"Step {step['step']}: Non-idempotent behavior detected")

                        if "should NOT appear" in expected.lower():
                            # Check if deleted entity still appears
                            data = step.get("data", [])
                            if data and len(data) > 0:
                                has_anomaly = True
                                anomaly_reasons.append(f"Step {step['step']}: Deleted entity still visible")

                        if "should fail" in expected.lower() and step.get("status") == "success":
                            has_anomaly = True
                            anomaly_reasons.append(f"Step {step['step']}: Operation succeeded when expected to fail")

                if has_anomaly:
                    classification["classification"] = "issue_ready"
                    classification["reasoning"] = "; ".join(anomaly_reasons)
                    review["classifications"]["issue_ready"].append(classification)
                    issue_ready_count += 1
                else:
                    classification["classification"] = "observation"
                    classification["reasoning"] = "State property tested, no anomaly detected"
                    review["classifications"]["observation"].append(classification)

    # Check minimum success criteria
    review["minimum_success_met"] = (
        primary_cases_completed >= 6 and
        (issue_ready_count >= 1 or any(c["classification"] == "observation" for c in review["classifications"]["observation"]))
    )

    review["primary_cases_completed"] = primary_cases_completed
    review["issue_ready_count"] = issue_ready_count

    return review


def main():
    parser = argparse.ArgumentParser(
        description="Run R3 sequence/state-based campaign"
    )
    parser.add_argument(
        "--adapter",
        default="milvus",
        choices=["mock", "milvus"],
        help="Adapter to use (default: milvus)"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Milvus host (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=19530,
        help="Milvus port (default: 19530)"
    )
    parser.add_argument(
        "--run-tag",
        default="r3-sequence",
        help="Run tag (default: r3-sequence)"
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Output directory (default: results)"
    )
    parser.add_argument(
        "--templates",
        default="casegen/templates/r3_sequence_state.yaml",
        help="Test template file (default: casegen/templates/r3_sequence_state.yaml)"
    )
    parser.add_argument(
        "--require-real",
        action="store_true",
        help="Require real Milvus connection; fail explicitly if connection fails"
    )

    args = parser.parse_args()

    # Generate run ID
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"r3-sequence-{args.run_tag}-{timestamp}"

    print(f"=== R3 Sequence/State-Based Campaign ===")
    print(f"Run ID: {run_id}")
    print(f"Adapter: {args.adapter}")
    print(f"Templates: {args.templates}")
    print()

    # Create adapter with explicit connection verification
    adapter = None
    adapter_type = args.adapter

    if args.adapter == "milvus":
        print(f"=== ENVIRONMENT SETUP ===")
        print(f"Target: Milvus at {args.host}:{args.port}")
        print()

        # Explicit connection attempt
        try:
            print(f"Attempting connection to Milvus at {args.host}:{args.port}...")
            connection_config = {
                "host": args.host,
                "port": args.port,
                "alias": "default"
            }

            # Create adapter and test connection
            adapter = MilvusAdapter(connection_config)

            if adapter.health_check():
                print(f"[OK] Successfully connected to Milvus")
                print(f"[OK] Health check passed")
                adapter_type = "milvus"
            else:
                raise Exception("Milvus health check failed")

        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Milvus connection failed: {error_msg}")
            print()

            if args.require_real:
                print("=== EXECUTION ABORTED ===")
                print("--require-real flag is set; cannot proceed without Milvus connection")
                print()
                print("Required actions:")
                print("1. Start Milvus: docker run -d -p 19530:19530 milvusdb/milvus:latest")
                print("2. Verify: docker ps | grep milvus")
                print("3. Check health: curl http://localhost:19530/health")
                print("4. Re-run this script")
                sys.exit(1)
            else:
                print("WARNING: --require-real flag NOT set")
                print("SILENT FALLBACK to mock adapter - this is NOT a real database campaign")
                print()
                print("To enforce real Milvus connection, use: --require-real")
                print()
                adapter = MockAdapter()
                adapter_type = "mock"
    else:
        adapter = MockAdapter()
        adapter_type = "mock"

    print()
    print(f"=== ADAPTER STATUS ===")
    print(f"Adapter Type: {adapter_type}")
    if adapter_type == "mock":
        print("WARNING: Using mock adapter - results are NOT real database behavior")
    print()

    print()

    # Load templates
    print("Loading sequence templates...")
    templates = load_sequence_templates(args.templates)
    print(f"Loaded {len(templates)} sequence templates")
    print()

    # Create substitutions
    substitutions = create_substitutions()

    # Create sequence cases
    cases = [SequenceCase(t, substitutions) for t in templates]

    # Execute sequences
    print("Executing sequence cases...")
    executor = SequenceExecutor(adapter, args.adapter)
    results = []

    for case in cases:
        result = executor.execute_sequence(case, run_id)
        results.append(result)
        print(f"    Status: {result['overall_status']}")

    print()
    print(f"Executed {len(results)} sequence cases")
    print()

    # Post-run review
    print("Performing post-run review...")
    review = post_run_review(results)

    print(f"Cases reviewed: {review['cases_reviewed']}")
    print(f"Primary cases completed: {review['primary_cases_completed']}")
    print(f"Classifications:")
    print(f"  Issue-ready: {len(review['classifications']['issue_ready'])}")
    print(f"  Observation: {len(review['classifications']['observation'])}")
    print(f"  Calibration: {len(review['classifications']['calibration'])}")
    print(f"  Exploratory: {len(review['classifications']['exploratory'])}")
    print()
    print(f"Minimum success criteria met: {review['minimum_success_met']}")
    print()

    # Write results
    output_dir = Path(args.output_dir) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write execution results
    results_file = output_dir / "execution_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    # Write review
    review_file = output_dir / "post_run_review.json"
    with open(review_file, 'w') as f:
        json.dump(review, f, indent=2)

    # Write metadata
    metadata = {
        "run_id": run_id,
        "run_tag": args.run_tag,
        "timestamp": datetime.now().isoformat(),
        "phase": "R3",
        "adapter_requested": args.adapter,
        "adapter_actual": adapter_type,
        "is_real_database_run": (adapter_type == "milvus"),
        "require_real_flag": args.require_real,
        "templates": args.templates,
        "case_count": len(cases),
        "minimum_success_met": review["minimum_success_met"],
        "classifications": {
            k: len(v) for k, v in review["classifications"].items()
        }
    }

    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"Results written to {output_dir}")
    print()

    # Summary
    print("=== Summary ===")
    print(f"Run ID: {run_id}")
    print(f"Adapter Requested: {args.adapter}")
    print(f"Adapter Actual: {adapter_type}")
    if adapter_type == "mock":
        print("WARNING: This was a MOCK run - NOT real database behavior")
    print(f"Total cases: {len(cases)}")
    print(f"Primary cases: {sum(1 for c in cases if c.type == 'primary')}")
    print(f"Calibration cases: {sum(1 for c in cases if c.type == 'calibration')}")
    print(f"Exploratory cases: {sum(1 for c in cases if c.type == 'exploratory')}")
    print(f"Minimum success: {'MET' if review['minimum_success_met'] else 'NOT MET'}")
    print(f"Evidence: {output_dir}")
    print()

    # Cleanup
    try:
        adapter.close()
    except Exception:
        pass

    print("Done!")


if __name__ == "__main__":
    main()
