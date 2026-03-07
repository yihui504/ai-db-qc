# Milvus-vs-seekdb Differential Campaign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a differential campaign that runs the same 30 high-yield test cases on both Milvus and seekdb, producing comparative analysis with explicit behavioral difference labels.

**Architecture:**
1. Shared case pack (30 cases) organized into 3 buckets: parameter boundaries, diagnostic quality, preconditions
2. Differential runner executes cases on both databases and collects results
3. Differential analyzer compares results and assigns explicit comparison labels
4. Output generator produces aggregate tables and differential case lists

**Tech Stack:**
- Existing adapters: adapters/seekdb_adapter.py (MySQL), adapters/milvus_adapter.py (REST)
- Existing framework: pipeline/, oracles/, schemas/
- New components: differential template, runner, analyzer
- Python 3.8+ (for Windows compatibility)

---

## Task 1: Create Shared Case Pack Template

**Files:**
- Create: `casegen/templates/differential_shared_pack.yaml`

**Step 1: Create template file structure**

Write the YAML file with 30 cases organized into 3 buckets:

```yaml
# Shared case pack for Milvus-vs-seekdb differential campaign
# All cases run on BOTH databases with identical parameters
# Total: 30 cases (10 per bucket)

templates:
  # ===== BUCKET 1: PARAMETER BOUNDARY / CONSTRAINTS (10 cases) =====

  - template_id: diff-boundary-001
    operation: create_collection
    param_template:
      collection_name: "test_boundary_{id}"
      dimension: 0  # ILLEGAL: minimum is 1
      metric_type: "L2"
    validity_category: invalid
    expected_validity: illegal
    bucket: parameter_boundary
    rationale: "Zero dimension - should be rejected with clear error"

  - template_id: diff-boundary-002
    operation: create_collection
    param_template:
      collection_name: "test_boundary_{id}"
      dimension: -1  # ILLEGAL: negative dimension
      metric_type: "L2"
    validity_category: invalid
    expected_validity: illegal
    bucket: parameter_boundary
    rationale: "Negative dimension - should be rejected"

  - template_id: diff-boundary-003
    operation: create_collection
    param_template:
      collection_name: "test_boundary_{id}"
      dimension: 99999  # EDGE CASE: very large dimension
      metric_type: "L2"
    validity_category: valid
    expected_validity: legal
    bucket: parameter_boundary
    rationale: "Very large dimension - may succeed or fail differently"

  - template_id: diff-boundary-004
    operation: search
    param_template:
      collection_name: "{collection}"
      vector: "{query_vector}"
      top_k: 0  # ILLEGAL: minimum is 1
    validity_category: invalid
    expected_validity: illegal
    bucket: parameter_boundary
    rationale: "Zero top_k - should be rejected"

  - template_id: diff-boundary-005
    operation: search
    param_template:
      collection_name: "{collection}"
      vector: "{query_vector}"
      top_k: -1  # ILLEGAL: negative top_k
    validity_category: invalid
    expected_validity: illegal
    bucket: parameter_boundary
    rationale: "Negative top_k - should be rejected"

  - template_id: diff-boundary-006
    operation: search
    param_template:
      collection_name: "{collection}"
      vector: "{query_vector}"
      top_k: 1000000  # EDGE CASE: very large top_k
    validity_category: valid
    expected_validity: legal
    bucket: parameter_boundary
    rationale: "Very large top_k - may have different limits"

  - template_id: diff-boundary-007
    operation: create_collection
    param_template:
      collection_name: "test_boundary_{id}"
      dimension: 128
      metric_type: "INVALID_METRIC"  # ILLEGAL: not in [L2, IP, COSINE]
    validity_category: invalid
    expected_validity: illegal
    bucket: parameter_boundary
    rationale: "Invalid metric type - should be rejected"

  - template_id: diff-boundary-008
    operation: create_collection
    param_template:
      collection_name: "test_boundary_{id}"
      dimension: 128
      metric_type: ""  # ILLEGAL: empty metric type
    validity_category: invalid
    expected_validity: illegal
    bucket: parameter_boundary
    rationale: "Empty metric type - should be rejected"

  - template_id: diff-boundary-009
    operation: insert
    param_template:
      collection_name: "{collection}"
      vectors: []  # ILLEGAL: empty vector list
    validity_category: invalid
    expected_validity: illegal
    bucket: parameter_boundary
    rationale: "Empty vector list - should be rejected"

  - template_id: diff-boundary-010
    operation: insert
    param_template:
      collection_name: "{collection}"
      vectors: "{wrong_dimension_vectors}"  # ILLEGAL: dimension mismatch
    validity_category: invalid
    expected_validity: illegal
    bucket: parameter_boundary
    rationale: "Dimension mismatch - should be rejected"

  # ===== BUCKET 2: DIAGNOSTIC QUALITY (10 cases) =====

  - template_id: diff-diag-001
    operation: create_collection
    param_template:
      collection_name: "test_diag_{id}"
      dimension: 0
      metric_type: "L2"
    validity_category: invalid
    expected_validity: illegal
    bucket: diagnostic_quality
    rationale: "Test diagnostic quality for invalid dimension"

  - template_id: diff-diag-002
    operation: create_collection
    param_template:
      collection_name: "test_diag_{id}"
      dimension: 128
      metric_type: "BOGUS_METRIC"
    validity_category: invalid
    expected_validity: illegal
    bucket: diagnostic_quality
    rationale: "Test diagnostic quality for invalid metric"

  - template_id: diff-diag-003
    operation: search
    param_template:
      collection_name: "{collection}"
      vector: "{query_vector}"
      top_k: -5
    validity_category: invalid
    expected_validity: illegal
    bucket: diagnostic_quality
    rationale: "Test diagnostic quality for negative top_k"

  - template_id: diff-diag-004
    operation: search
    param_template:
      collection_name: "nonexistent_collection"  # ILLEGAL: doesn't exist
      vector: "{query_vector}"
      top_k: 10
    validity_category: invalid
    expected_validity: illegal
    bucket: diagnostic_quality
    rationale: "Test diagnostic quality for non-existent collection"

  - template_id: diff-diag-005
    operation: insert
    param_template:
      collection_name: "nonexistent_collection"  # ILLEGAL: doesn't exist
      vectors: "{vectors}"
    validity_category: invalid
    expected_validity: illegal
    bucket: diagnostic_quality
    rationale: "Test diagnostic quality for insert into non-existent collection"

  - template_id: diff-diag-006
    operation: insert
    param_template:
      collection_name: "{collection}"
      vectors: "{wrong_dimension_vectors}"
    validity_category: invalid
    expected_validity: illegal
    bucket: diagnostic_quality
    rationale: "Test diagnostic quality for dimension mismatch"

  - template_id: diff-diag-007
    operation: delete
    param_template:
      collection_name: "{collection}"
      ids: []  # ILLEGAL: empty ID list
    validity_category: invalid
    expected_validity: illegal
    bucket: diagnostic_quality
    rationale: "Test diagnostic quality for empty delete list"

  - template_id: diff-diag-008
    operation: delete
    param_template:
      collection_name: "nonexistent_collection"  # ILLEGAL: doesn't exist
      ids: [1, 2, 3]
    validity_category: invalid
    expected_validity: illegal
    bucket: diagnostic_quality
    rationale: "Test diagnostic quality for delete from non-existent collection"

  - template_id: diff-diag-009
    operation: search
    param_template:
      collection_name: "{collection}"
      vector: []  # ILLEGAL: empty vector
      top_k: 10
    validity_category: invalid
    expected_validity: illegal
    bucket: diagnostic_quality
    rationale: "Test diagnostic quality for empty query vector"

  - template_id: diff-diag-010
    operation: insert
    param_template:
      collection_name: "{collection}"
      vectors: [[0.1] * 128, [0.2] * 128]
    validity_category: valid
    expected_validity: legal
    required_preconditions:
      - collection_exists
    bucket: diagnostic_quality
    rationale: "Valid insert - test success message quality"

  # ===== BUCKET 3: PRECONDITION / STATE HANDLING (10 cases) =====

  - template_id: diff-precond-001
    operation: search
    param_template:
      collection_name: "nonexistent_collection"
      vector: "{query_vector}"
      top_k: 10
    validity_category: pseudo_valid
    expected_validity: legal  # Contract-valid but precondition-fail
    required_preconditions:
      - collection_exists
    bucket: precondition_state
    rationale: "Search on non-existent collection - test precondition handling"

  - template_id: diff-precond-002
    operation: insert
    param_template:
      collection_name: "nonexistent_collection"
      vectors: "{vectors}"
    validity_category: pseudo_valid
    expected_validity: legal  # Contract-valid but precondition-fail
    required_preconditions:
      - collection_exists
    bucket: precondition_state
    rationale: "Insert into non-existent collection - test precondition handling"

  - template_id: diff-precond-003
    operation: delete
    param_template:
      collection_name: "nonexistent_collection"
      ids: [1, 2, 3]
    validity_category: pseudo_valid
    expected_validity: legal  # Contract-valid but precondition-fail
    required_preconditions:
      - collection_exists
    bucket: precondition_state
    rationale: "Delete from non-existent collection - test precondition handling"

  - template_id: diff-precond-004
    operation: search
    param_template:
      collection_name: "{empty_collection}"  # Exists but has no data
      vector: "{query_vector}"
      top_k: 10
    validity_category: pseudo_valid
    expected_validity: legal  # Contract-valid but edge-case
    required_preconditions:
      - collection_exists
    bucket: precondition_state
    rationale: "Search on empty collection - test behavior"

  - template_id: diff-precond-005
    operation: search
    param_template:
      collection_name: "{collection}"
      vector: "{query_vector}"
      top_k: 10
    validity_category: pseudo_valid
    expected_validity: legal  # Contract-valid but index not loaded
    required_preconditions:
      - collection_exists
      - index_built
      - index_loaded
    bucket: precondition_state
    rationale: "Search before index load - test precondition handling"

  - template_id: diff-precond-006
    operation: insert
    param_template:
      collection_name: "{collection}"
      vectors: "{vectors}"
    validity_category: pseudo_valid
    expected_validity: legal  # Contract-valid but schema mismatch
    required_preconditions:
      - collection_exists
    bucket: precondition_state
    rationale: "Insert with schema variation - test tolerance"

  - template_id: diff-precond-007
    operation: search
    param_template:
      collection_name: "{collection}"
      vector: "{query_vector}"
      top_k: 10
    validity_category: valid
    expected_validity: legal
    required_preconditions:
      - collection_exists
      - index_built
      - index_loaded
    bucket: precondition_state
    rationale: "Valid search with all preconditions - baseline"

  - template_id: diff-precond-008
    operation: insert
    param_template:
      collection_name: "{collection}"
      vectors: "{vectors}"
    validity_category: valid
    expected_validity: legal
    required_preconditions:
      - collection_exists
    bucket: precondition_state
    rationale: "Valid insert - baseline"

  - template_id: diff-precond-009
    operation: create_collection
    param_template:
      collection_name: "test_precond_{id}"
      dimension: 128
      metric_type: "L2"
    validity_category: valid
    expected_validity: legal
    required_preconditions: []
    bucket: precondition_state
    rationale: "Valid collection creation - baseline"

  - template_id: diff-precond-010
    operation: drop_collection
    param_template:
      collection_name: "nonexistent_collection"
    validity_category: pseudo_valid
    expected_validity: legal  # Contract-valid but doesn't exist
    required_preconditions:
      - collection_exists
    bucket: precondition_state
    rationale: "Drop non-existent collection - test behavior"
```

**Step 2: Verify YAML syntax**

Run: `python -c "import yaml; yaml.safe_load(open('casegen/templates/differential_shared_pack.yaml'))"`
Expected: No syntax errors

**Step 3: Commit**

```bash
git add casegen/templates/differential_shared_pack.yaml
git commit -m "feat: add shared differential case pack (30 cases, 3 buckets)"
```

---

## Task 2: Create Differential Campaign Runner

**Files:**
- Create: `scripts/run_differential_campaign.py`

**Step 1: Write runner skeleton**

Create the main runner script:

```python
"""Run differential campaign on Milvus and seekdb.

Executes the same 30 shared cases on both databases,
producing side-by-side comparison results.

Usage:
    python scripts/run_differential_campaign.py --run-tag <tag>
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from adapters.seekdb_adapter import SeekDBAdapter
    from adapters.milvus_adapter import MilvusAdapter
    from casegen.generators.instantiator import load_templates, instantiate_all
    from contracts.core.loader import get_default_contract
    from contracts.db_profiles.loader import load_profile
    from pipeline.preconditions import PreconditionEvaluator
    from pipeline.executor import Executor
    from pipeline.triage import Triage
    from schemas.common import ObservedOutcome
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


def run_campaign_on_db(adapter, adapter_name: str, cases: List, run_id: str) -> Dict:
    """Run campaign on a single database.

    Returns dict with:
        - results: list of execution results
        - triage_results: list of triage classifications
        - metadata: campaign metadata
    """
    print(f"\n{'='*60}")
    print(f"  Running campaign on {adapter_name}")
    print(f"{'='*60}\n")

    # Load contract and profile
    contract = get_default_contract()
    if adapter_name == "seekdb":
        profile = load_profile("contracts/db_profiles/seekdb_profile.yaml")
    else:  # milvus
        profile = load_profile("contracts/db_profiles/milvus_profile.yaml")

    # Get runtime snapshot
    snapshot = adapter.get_runtime_snapshot()

    # Create runtime context
    runtime_context = {
        "collections": snapshot.get("collections", []),
        "indexed_collections": snapshot.get("indexed_collections", []),
        "loaded_collections": snapshot.get("loaded_collections", []),
        "connected": snapshot.get("connected", True),
        "supported_features": ["hybrid_search", "filtering", "multi_model"]
    }

    # Create executor
    precond = PreconditionEvaluator(contract, profile, runtime_context)
    precond.load_runtime_snapshot(snapshot)

    # Use minimal oracles for differential campaign
    from oracles.filter_strictness import FilterStrictness
    from oracles.write_read_consistency import WriteReadConsistency
    from oracles.monotonicity import Monotonicity

    oracles = [
        WriteReadConsistency(validate_ids=True),
        FilterStrictness(),
        Monotonicity()
    ]

    executor = Executor(adapter, precond, oracles)

    triage = Triage()

    # Execute cases
    results = []
    for case in cases:
        print(f"  [{adapter_name}] Executing: {case.case_id}")
        try:
            result = executor.execute_case(case, run_id)
            results.append(result)
        except Exception as e:
            print(f"  [{adapter_name}] ERROR: {e}")
            # Create minimal error result
            from schemas.case import ExecutionResult
            result = ExecutionResult(
                case_id=case.case_id,
                run_id=run_id,
                status="error",
                observed_outcome=ObservedOutcome.FAILURE,
                error=str(e)
            )
            results.append(result)

    # Classify bugs
    triage_results = []
    for case in cases:
        result = next((r for r in results if r.case_id == case.case_id), None)
        if result:
            triage_result = triage.classify(case, result, naive=False)
            triage_results.append(triage_result)

    success_count = sum(1 for r in results if r.observed_outcome == ObservedOutcome.SUCCESS)
    failure_count = sum(1 for r in results if r.observed_outcome == ObservedOutcome.FAILURE)

    print(f"\n[{adapter_name}] Campaign complete:")
    print(f"  Success: {success_count}")
    print(f"  Failure: {failure_count}")
    print(f"  Bugs triaged: {sum(1 for t in triage_results if t is not None)}")

    return {
        "adapter_name": adapter_name,
        "results": results,
        "triage_results": triage_results,
        "snapshot": snapshot,
        "success_count": success_count,
        "failure_count": failure_count
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run differential campaign on Milvus and seekdb"
    )
    parser.add_argument(
        "--run-tag",
        required=True,
        help="Run tag for identification"
    )
    parser.add_argument(
        "--seekdb-endpoint",
        default=os.getenv("SEEKDB_API_ENDPOINT", "127.0.0.1:2881"),
        help="seekdb host:port"
    )
    parser.add_argument(
        "--seekdb-api-key",
        default=os.getenv("SEEKDB_API_KEY", ""),
        help="seekdb API key (not used for SQL)"
    )
    parser.add_argument(
        "--milvus-endpoint",
        default=os.getenv("MILVUS_API_ENDPOINT", "http://localhost:19530"),
        help="Milvus API endpoint"
    )
    parser.add_argument(
        "--skip-milvus",
        action="store_true",
        help="Skip Milvus campaign (seekdb-only)"
    )
    parser.add_argument(
        "--skip-seekdb",
        action="store_true",
        help="Skip seekdb campaign (Milvus-only)"
    )
    parser.add_argument(
        "--output-dir",
        default="runs",
        help="Output directory"
    )

    args = parser.parse_args()

    # Generate run ID
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"differential-{args.run_tag}-{timestamp}"

    print("="*60)
    print("  Milvus-vs-seekdb Differential Campaign")
    print("="*60)
    print(f"Run ID: {run_id}")
    print(f"Run Tag: {args.run_tag}")
    print()

    # Load shared case pack
    print("Loading shared case pack...")
    templates = load_templates("casegen/templates/differential_shared_pack.yaml")
    print(f"Loaded {len(templates)} templates")

    # Instantiate with basic parameters
    cases = instantiate_all(templates, {
        "collection": "diff_test_collection",
        "query_vector": [0.1] * 128,
        "vectors": [[0.1] * 128, [0.2] * 128],
        "k": 10,
        "wrong_dimension_vectors": [[0.1] * 64],  # Wrong dimension
        "empty_collection": "diff_empty_collection"
    })
    print(f"Instantiated {len(cases)} cases\n")

    # Track results
    campaign_results = {}

    # Run on seekdb
    if not args.skip_seekdb:
        try:
            seekdb_adapter = SeekDBAdapter(
                api_endpoint=args.seekdb_endpoint,
                api_key=args.seekdb_api_key,
                collection="diff_test_collection"
            )

            if not seekdb_adapter.health_check():
                print("ERROR: seekdb health check failed")
                print("Please ensure seekdb is running at", args.seekdb_endpoint)
                if not args.skip_milvus:
                    print("Continuing with Milvus-only campaign...")
                else:
                    return 1
            else:
                campaign_results["seekdb"] = run_campaign_on_db(
                    seekdb_adapter, "seekdb", cases, run_id
                )
        except Exception as e:
            print(f"ERROR: seekdb campaign failed: {e}")
            if not args.skip_milvus:
                print("Continuing with Milvus-only campaign...")
            else:
                return 1

    # Run on Milvus
    if not args.skip_milvus:
        try:
            milvus_adapter = MilvusAdapter(
                api_endpoint=args.milvus_endpoint,
                collection="diff_test_collection"
            )

            if not milvus_adapter.health_check():
                print("ERROR: Milvus health check failed")
                print("Please ensure Milvus is running at", args.milvus_endpoint)
                if not args.skip_seekdb:
                    print("Continuing with seekdb-only campaign...")
                else:
                    return 1
            else:
                campaign_results["milvus"] = run_campaign_on_db(
                    milvus_adapter, "milvus", cases, run_id
                )
        except Exception as e:
            print(f"ERROR: Milvus campaign failed: {e}")
            if campaign_results.get("seekdb"):
                print("Continuing with seekdb-only results...")
            else:
                return 1

    # Save raw results
    output_dir = Path(args.output_dir) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    import json
    for db_name, data in campaign_results.items():
        db_dir = output_dir / db_name
        db_dir.mkdir(exist_ok=True)

        # Save results
        with open(db_dir / "execution_results.jsonl", "w") as f:
            for result in data["results"]:
                f.write(json.dumps(result.__dict__ if hasattr(result, '__dict__') else result) + "\n")

        # Save triage
        with open(db_dir / "triage_results.json", "w") as f:
            triage_list = []
            for t in data["triage_results"]:
                if t is not None:
                    triage_list.append(t.__dict__ if hasattr(t, '__dict__') else t)
                else:
                    triage_list.append(None)
            json.dump(triage_list, f, indent=2)

        # Save metadata
        with open(db_dir / "metadata.json", "w") as f:
            json.dump({
                "adapter_name": data["adapter_name"],
                "success_count": data["success_count"],
                "failure_count": data["failure_count"],
                "snapshot": data["snapshot"]
            }, f, indent=2)

    print(f"\nRaw results saved to {output_dir}")
    print(f"\nNext step: Run differential analyzer")
    print(f"  python scripts/analyze_differential_results.py {output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Test runner import**

Run: `python -c "from scripts.run_differential_campaign import main; print('Import OK')"`
Expected: "Import OK" (may have import errors for missing adapters, fix as needed)

**Step 3: Commit**

```bash
git add scripts/run_differential_campaign.py
git commit -m "feat: add differential campaign runner"
```

---

## Task 3: Create Differential Analyzer

**Files:**
- Create: `scripts/analyze_differential_results.py`

**Step 1: Write analyzer with comparison labels**

Create the differential analyzer:

```python
"""Analyze differential campaign results and produce comparison report.

Reads results from both databases, compares outcomes,
and assigns explicit comparison labels.

Usage:
    python scripts/analyze_differential_results.py <run_directory>
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Differential comparison labels
DIFF_LABELS = {
    "same_behavior": "Both databases behaved identically",
    "seekdb_stricter": "seekdb rejected input that Milvus accepted",
    "milvus_stricter": "Milvus rejected input that seekdb accepted",
    "seekdb_poorer_diagnostic": "Both rejected but seekdb had worse error message",
    "milvus_poorer_diagnostic": "Both rejected but Milvus had worse error message",
    "seekdb_precondition_sensitive": "seekdb failed due to precondition, Milvus didn't",
    "milvus_precondition_sensitive": "Milvus failed due to precondition, seekdb didn't",
    "outcome_difference": "Different outcomes (other than above categories)",
    "triage_difference": "Same outcome but different triage classification",
}


class DifferentialAnalyzer:
    """Analyze and compare results from two databases."""

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)
        self.milvus_dir = self.run_dir / "milvus"
        self.seekdb_dir = self.run_dir / "seekdb"

        # Load results
        self.milvus_results = self._load_results(self.milvus_dir)
        self.seekdb_results = self._load_results(self.seekdb_dir)

        # Load triage
        self.milvus_triage = self._load_triage(self.milvus_dir)
        self.seekdb_triage = self._load_triage(self.seekdb_dir)

    def _load_results(self, db_dir: Path) -> Dict[str, Dict]:
        """Load execution results from database directory."""
        results = {}
        results_file = db_dir / "execution_results.jsonl"

        if not results_file.exists():
            return results

        with open(results_file, "r") as f:
            for line in f:
                data = json.loads(line)
                case_id = data.get("case_id")
                if case_id:
                    results[case_id] = data

        return results

    def _load_triage(self, db_dir: Path) -> Dict[str, Optional[Dict]]:
        """Load triage results from database directory."""
        triage = {}
        triage_file = db_dir / "triage_results.json"

        if not triage_file.exists():
            return triage

        with open(triage_file, "r") as f:
            data_list = json.load(f)
            # Need case_id from results to index properly
            # We'll match by index for now
            return data_list

        return triage

    def compare_case(self, case_id: str, milvus_result: Dict, seekdb_result: Dict) -> Dict:
        """Compare a single case across both databases.

        Returns dict with comparison data including label.
        """
        comparison = {
            "case_id": case_id,
            "milvus_outcome": milvus_result.get("observed_outcome", "unknown"),
            "seekdb_outcome": seekdb_result.get("observed_outcome", "unknown"),
            "milvus_error": milvus_result.get("error", ""),
            "seekdb_error": seekdb_result.get("error", ""),
            "milvus_status": milvus_result.get("status", ""),
            "seekdb_status": seekdb_result.get("status", ""),
        }

        # Determine comparison label
        comparison["label"] = self._assign_label(comparison)
        comparison["label_description"] = DIFF_LABELS.get(comparison["label"], "Unknown")

        return comparison

    def _assign_label(self, comparison: Dict) -> str:
        """Assign differential comparison label."""
        milvus_outcome = comparison["milvus_outcome"]
        seekdb_outcome = comparison["seekdb_outcome"]
        milvus_error = comparison.get("milvus_error", "")
        seekdb_error = comparison.get("seekdb_error", "")

        # Both succeeded
        if milvus_outcome == "success" and seekdb_outcome == "success":
            return "same_behavior"

        # Both failed
        if milvus_outcome == "failure" and seekdb_outcome == "failure":
            # Check for precondition differences
            if "not exist" in milvus_error.lower() and "not exist" not in seekdb_error.lower():
                return "milvus_precondition_sensitive"
            if "not exist" in seekdb_error.lower() and "not exist" not in milvus_error.lower():
                return "seekdb_precondition_sensitive"

            # Check diagnostic quality (heuristic: specific > generic)
            milvus_specific = self._is_specific_error(milvus_error)
            seekdb_specific = self._is_specific_error(seekdb_error)

            if milvus_specific and not seekdb_specific:
                return "seekdb_poorer_diagnostic"
            if seekdb_specific and not milvus_specific:
                return "milvus_poorer_diagnostic"

            # Same failure behavior
            return "same_behavior"

        # One succeeded, one failed
        if milvus_outcome == "success" and seekdb_outcome == "failure":
            return "seekdb_stricter"
        if milvus_outcome == "failure" and seekdb_outcome == "success":
            return "milvus_stricter"

        # Other differences
        return "outcome_difference"

    def _is_specific_error(self, error: str) -> bool:
        """Check if error message is specific (mentions parameter name or value)."""
        if not error:
            return False

        specific_keywords = [
            "dimension", "top_k", "metric", "collection",
            "must be", "required", "invalid", "expected"
        ]

        error_lower = error.lower()
        return any(kw in error_lower for kw in specific_keywords)

    def generate_report(self) -> Dict:
        """Generate complete differential report."""
        # Get all case IDs
        all_case_ids = set(self.milvus_results.keys()) | set(self.seekdb_results.keys())

        comparisons = []
        differential_cases = []

        for case_id in sorted(all_case_ids):
            milvus_result = self.milvus_results.get(case_id, {})
            seekdb_result = self.seekdb_results.get(case_id, {})

            if not milvus_result or not seekdb_result:
                # Case missing from one database
                continue

            comparison = self.compare_case(case_id, milvus_result, seekdb_result)
            comparisons.append(comparison)

            # Track differential cases (non-identical behavior)
            if comparison["label"] != "same_behavior":
                differential_cases.append(comparison)

        # Generate aggregate statistics
        label_counts = {}
        for comp in comparisons:
            label = comp["label"]
            label_counts[label] = label_counts.get(label, 0) + 1

        return {
            "comparisons": comparisons,
            "differential_cases": differential_cases,
            "total_cases": len(comparisons),
            "differential_count": len(differential_cases),
            "label_counts": label_counts,
            "generated_at": datetime.now().isoformat()
        }


def main():
    parser = argparse.ArgumentParser(
        description="Analyze differential campaign results"
    )
    parser.add_argument(
        "run_dir",
        help="Differential campaign run directory"
    )
    parser.add_argument(
        "--output",
        help="Output report file (default: <run_dir>/differential_report.json)"
    )

    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"ERROR: Run directory not found: {run_dir}")
        return 1

    print("="*60)
    print("  Differential Analysis")
    print("="*60)
    print(f"Run directory: {run_dir}")
    print()

    # Analyze
    analyzer = DifferentialAnalyzer(run_dir)
    report = analyzer.generate_report()

    # Print summary
    print(f"Total cases compared: {report['total_cases']}")
    print(f"Differential cases: {report['differential_count']}")
    print()
    print("Label breakdown:")
    for label, count in sorted(report["label_counts"].items()):
        desc = DIFF_LABELS.get(label, label)
        print(f"  {count:2d} {label}: {desc}")

    # Save report
    output_file = Path(args.output) if args.output else run_dir / "differential_report.json"
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    print()
    print(f"Report saved to: {output_file}")

    # Generate markdown report
    markdown_file = run_dir / "differential_report.md"
    generate_markdown_report(report, markdown_file)
    print(f"Markdown report saved to: {markdown_file}")

    return 0


def generate_markdown_report(report: Dict, output_file: Path):
    """Generate human-readable markdown report."""

    lines = [
        "# Milvus-vs-seekdb Differential Report",
        "",
        f"**Generated**: {report['generated_at']}",
        f"**Total Cases**: {report['total_cases']}",
        f"**Differential Cases**: {report['differential_count']}",
        "",
        "## Aggregate Comparison",
        "",
        "| Label | Count | Description |",
        "|-------|-------|-------------|"
    ]

    for label, count in sorted(report["label_counts"].items()):
        desc = DIFF_LABELS.get(label, label)
        lines.append(f"| {label} | {count} | {desc} |")

    lines.extend([
        "",
        "## Differential Case List",
        "",
        "Cases with different behavior between Milvus and seekdb:",
        "",
        "| Case ID | Label | Milvus Outcome | seekdb Outcome | Milvus Error | seekdb Error |",
        "|---------|-------|----------------|-----------------|---------------|--------------|"
    ])

    for case in report["differential_cases"]:
        lines.append(
            f"| {case['case_id']} | {case['label']} | {case['milvus_outcome']} | "
            f"{case['seekdb_outcome']} | {case['milvus_error'][:50]}... | "
            f"{case['seekdb_error'][:50]}... |"
        )

    lines.extend([
        "",
        "## All Cases Comparison",
        "",
        "| Case ID | Label | Milvus | seekdb |",
        "|---------|-------|--------|--------|"
    ])

    for case in report["comparisons"]:
        milvus_symbol = "✓" if case["milvus_outcome"] == "success" else "✗"
        seekdb_symbol = "✓" if case["seekdb_outcome"] == "success" else "✗"
        lines.append(
            f"| {case['case_id']} | {case['label']} | {milvus_symbol} {case['milvus_outcome']} | "
            f"{seekdb_symbol} {case['seekdb_outcome']} |"
        )

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Test analyzer structure**

Run: `python scripts/analyze_differential_results.py --help`
Expected: Help message displayed

**Step 3: Commit**

```bash
git add scripts/analyze_differential_results.py
git commit -m "feat: add differential analyzer with comparison labels"
```

---

## Task 4: End-to-End Test

**Step 1: Run seekdb-only campaign first**

```bash
# Make sure seekdb is running
docker ps | grep seekdb

# Run differential campaign (Milvus-only first since we may not have Milvus)
cd C:/Users/11428/Desktop/ai-db-qc
PYTHONPATH="C:/Users/11428/Desktop/ai-db-qc" python scripts/run_differential_campaign.py \
    --run-tag test \
    --skip-milvus \
    --seekdb-endpoint 127.0.0.1:2881
```

Expected: Campaign runs on seekdb, results saved to `runs/differential-test-*/`

**Step 2: Run differential analysis**

```bash
python scripts/analyze_differential_results.py runs/differential-test-<timestamp>
```

Expected: Analysis runs, report generated (even with only seekdb data)

**Step 3: Verify outputs**

Run: `ls runs/differential-test-<timestamp>/`
Expected: `seekdb/`, `differential_report.json`, `differential_report.md`

**Step 4: Commit**

```bash
git add runs/differential-test-*/
git commit -m "test: add differential test run results"
```

---

## Task 5: Full Differential Campaign (when Milvus available)

**Step 1: Ensure Milvus is running**

```bash
# Check Milvus status
curl http://localhost:19530/healthz
```

Expected: Milvus health check response

**Step 2: Run full differential campaign**

```bash
cd C:/Users/11428/Desktop/ai-db-qc
PYTHONPATH="C:/Users/11428/Desktop/ai-db-qc" python scripts/run_differential_campaign.py \
    --run-tag milvus-seekdb-comparison \
    --milvus-endpoint http://localhost:19530 \
    --seekdb-endpoint 127.0.0.1:2881
```

Expected: Campaign runs on both databases, results saved

**Step 3: Generate comprehensive analysis**

```bash
python scripts/analyze_differential_results.py runs/differential-milvus-seekdb-comparison-<timestamp>
```

Expected: Full differential report with comparison labels

**Step 4: Review outputs**

- `differential_report.json` - Machine-readable comparison
- `differential_report.md` - Human-readable report

**Step 5: Commit final results**

```bash
git add runs/differential-milvus-seekdb-comparison-*/
git commit -m "feat: complete Milvus-vs-seekdb differential campaign"
```

---

## Success Criteria

After implementation:

- [ ] Shared case pack: 30 cases (10 per bucket)
- [ ] Runner executes on both databases with same cases
- [ ] Analyzer produces comparison labels for each case
- [ ] Aggregate comparison table shows label distribution
- [ ] Differential case list highlights behavioral differences
- [ ] At least 2 differential cases identified (expected)
- [ ] Reports saved in both JSON and Markdown formats

---

## Notes

1. **Milvus adapter**: The plan assumes `adapters/milvus_adapter.py` exists. If not, create a minimal Milvus adapter similar to seekdb's structure.

2. **Parameter mapping**: seekdb uses MySQL protocol, Milvus uses REST. Parameter mapping happens in adapters, so the same test cases work for both.

3. **Triage consistency**: Both databases use the same triage logic, ensuring fair comparison.

4. **Bucket analysis**: Cases are tagged by bucket in template, allowing bucket-specific analysis if needed.
