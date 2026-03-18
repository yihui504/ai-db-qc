"""Phase 5.3 evaluation runner with proper ablation demonstrations."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is on the path when invoked as a subprocess
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from casegen.generators.instantiator import load_templates, instantiate_all
    from contracts.core.loader import get_default_contract
    from contracts.db_profiles.loader import load_profile
    from pipeline.preconditions import PreconditionEvaluator
    from adapters.mock import MockAdapter, ResponseMode, DiagnosticQuality
    from adapters.milvus_adapter import MilvusAdapter
    from oracles.write_read_consistency import WriteReadConsistency
    from oracles.filter_strictness import FilterStrictness
    from oracles.monotonicity import Monotonicity
    from pipeline.executor import Executor
    from pipeline.triage import Triage
    from evidence.writer import EvidenceWriter
    from evidence.fingerprint import capture_environment
    from schemas.case import TestCase
    from schemas.common import OperationType, ObservedOutcome
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed")
    sys.exit(1)


class VariantFlags:
    """Container for experiment variant flags."""

    def __init__(
        self,
        no_gate: bool = False,
        no_oracle: bool = False,
        naive_triage: bool = False,
        adapter_fallback: bool = False,
        adapter_fallback_reason: str = ""
    ):
        self.no_gate = no_gate
        self.no_oracle = no_oracle
        self.naive_triage = naive_triage
        self.adapter_fallback = adapter_fallback
        self.adapter_fallback_reason = adapter_fallback_reason

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for metadata storage."""
        return {
            "no_gate": self.no_gate,
            "no_oracle": self.no_oracle,
            "naive_triage": self.naive_triage,
            "adapter_fallback": self.adapter_fallback,
            "adapter_fallback_reason": self.adapter_fallback_reason
        }


def create_adapter_with_fallback(
    adapter_choice: str,
    host: str,
    port: int,
    require_real: bool = False,
    diagnostic_quality: str = "full",
    response_mode: str = "success",
    qdrant_url: str = "http://localhost:6333",
    weaviate_host: str = "localhost",
    weaviate_port: int = 8080,
    pgvector_container: str = "pgvector",
    pgvector_db: str = "vectordb",
) -> tuple[Any, VariantFlags, Dict[str, str]]:
    """Create adapter with fallback to mock. Supports mock/milvus/qdrant/weaviate/pgvector."""
    variant_flags = VariantFlags()
    adapter_requested = adapter_choice

    if adapter_choice == "mock":
        # Map string quality to enum
        quality_map = {
            "full": DiagnosticQuality.FULL,
            "partial": DiagnosticQuality.PARTIAL,
            "none": DiagnosticQuality.NONE
        }
        quality = quality_map.get(diagnostic_quality, DiagnosticQuality.FULL)
        # Map string response mode to enum
        response_mode_map = {
            "success": ResponseMode.SUCCESS,
            "failure": ResponseMode.FAILURE
        }
        mode = response_mode_map.get(response_mode, ResponseMode.SUCCESS)
        return (
            MockAdapter(response_mode=mode, diagnostic_quality=quality),
            variant_flags,
            {
                "adapter_requested": adapter_requested,
                "adapter_actual": "mock",
                "adapter_fallback": False,
                "fallback_reason": None
            }
        )

    if adapter_choice == "qdrant":
        try:
            from adapters.qdrant_adapter import QdrantAdapter
            adapter = QdrantAdapter({"url": qdrant_url})
            if adapter.health_check():
                print(f"Successfully connected to Qdrant at {qdrant_url}")
                return (
                    adapter,
                    variant_flags,
                    {
                        "adapter_requested": adapter_requested,
                        "adapter_actual": "qdrant",
                        "adapter_fallback": False,
                        "fallback_reason": None
                    }
                )
            raise Exception("Qdrant health check failed")
        except Exception as e:
            error_msg = str(e)
            print(f"ERROR: Qdrant connection failed: {error_msg}")
            if require_real:
                raise SystemExit(1) from e
            print("WARNING: Falling back to mock adapter")
            variant_flags.adapter_fallback = True
            variant_flags.adapter_fallback_reason = error_msg
            return (
                MockAdapter(response_mode=ResponseMode.SUCCESS),
                variant_flags,
                {"adapter_requested": adapter_requested, "adapter_actual": "mock",
                 "adapter_fallback": True, "fallback_reason": error_msg}
            )

    if adapter_choice == "weaviate":
        try:
            from adapters.weaviate_adapter import WeaviateAdapter
            adapter = WeaviateAdapter({"host": weaviate_host, "port": weaviate_port})
            if adapter.health_check():
                print(f"Successfully connected to Weaviate at {weaviate_host}:{weaviate_port}")
                return (
                    adapter,
                    variant_flags,
                    {
                        "adapter_requested": adapter_requested,
                        "adapter_actual": "weaviate",
                        "adapter_fallback": False,
                        "fallback_reason": None
                    }
                )
            raise Exception("Weaviate health check failed")
        except Exception as e:
            error_msg = str(e)
            print(f"ERROR: Weaviate connection failed: {error_msg}")
            if require_real:
                raise SystemExit(1) from e
            print("WARNING: Falling back to mock adapter")
            variant_flags.adapter_fallback = True
            variant_flags.adapter_fallback_reason = error_msg
            return (
                MockAdapter(response_mode=ResponseMode.SUCCESS),
                variant_flags,
                {"adapter_requested": adapter_requested, "adapter_actual": "mock",
                 "adapter_fallback": True, "fallback_reason": error_msg}
            )

    if adapter_choice == "pgvector":
        try:
            from adapters.pgvector_adapter import PgvectorAdapter
            adapter = PgvectorAdapter({
                "container": pgvector_container,
                "database": pgvector_db,
                "user": "postgres",
                "password": "pgvector",
            })
            if adapter.health_check():
                print(f"Successfully connected to pgvector at {pgvector_container}/{pgvector_db}")
                return (
                    adapter,
                    variant_flags,
                    {
                        "adapter_requested": adapter_requested,
                        "adapter_actual": "pgvector",
                        "adapter_fallback": False,
                        "fallback_reason": None
                    }
                )
            raise Exception("pgvector health check failed")
        except Exception as e:
            error_msg = str(e)
            print(f"ERROR: pgvector connection failed: {error_msg}")
            if require_real:
                raise SystemExit(1) from e
            print("WARNING: Falling back to mock adapter")
            variant_flags.adapter_fallback = True
            variant_flags.adapter_fallback_reason = error_msg
            return (
                MockAdapter(response_mode=ResponseMode.SUCCESS),
                variant_flags,
                {"adapter_requested": adapter_requested, "adapter_actual": "mock",
                 "adapter_fallback": True, "fallback_reason": error_msg}
            )

    # Default: milvus
    try:
        print(f"Connecting to Milvus at {host}:{port}...")
        connection_config = {
            "host": host,
            "port": port,
            "alias": "default"
        }
        adapter = MilvusAdapter(connection_config)

        if adapter.health_check():
            print(f"Successfully connected to Milvus")
            return (
                adapter,
                variant_flags,
                {
                    "adapter_requested": adapter_requested,
                    "adapter_actual": "milvus",
                    "adapter_fallback": False,
                    "fallback_reason": None
                }
            )
        else:
            raise Exception("Milvus health check failed")

    except Exception as e:
        error_msg = str(e)
        print(f"ERROR: Milvus connection failed: {error_msg}")

        if require_real:
            print("--require-real flag is set; failing instead of falling back to mock")
            raise SystemExit(1) from e

        print("WARNING: Falling back to mock adapter (data will NOT reflect real Milvus behavior)")
        variant_flags.adapter_fallback = True
        variant_flags.adapter_fallback_reason = error_msg
        # Map string quality to enum
        quality_map = {
            "full": DiagnosticQuality.FULL,
            "partial": DiagnosticQuality.PARTIAL,
            "none": DiagnosticQuality.NONE
        }
        quality = quality_map.get(diagnostic_quality, DiagnosticQuality.FULL)
        # Map string response mode to enum
        response_mode_map = {
            "success": ResponseMode.SUCCESS,
            "failure": ResponseMode.FAILURE
        }
        mode = response_mode_map.get(response_mode, ResponseMode.SUCCESS)
        return (
            MockAdapter(response_mode=mode, diagnostic_quality=quality),
            variant_flags,
            {
                "adapter_requested": adapter_requested,
                "adapter_actual": "mock",
                "adapter_fallback": True,
                "fallback_reason": error_msg
            }
        )


def create_oracles(variant_flags: VariantFlags) -> List[Any]:
    """Create oracle list based on variant flags."""
    if variant_flags.no_oracle:
        return []
    return [WriteReadConsistency(validate_ids=True), FilterStrictness(), Monotonicity()]


def main():
    parser = argparse.ArgumentParser(
        description="Run Phase 5.3 evaluation with comprehensive test cases"
    )
    parser.add_argument(
        "--adapter",
        default="milvus",
        choices=["mock", "milvus", "qdrant", "weaviate", "pgvector"],
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
        "--qdrant-url",
        default="http://localhost:6333",
        help="Qdrant URL (default: http://localhost:6333)"
    )
    parser.add_argument(
        "--weaviate-host",
        default="localhost",
        help="Weaviate host (default: localhost)"
    )
    parser.add_argument(
        "--weaviate-port",
        type=int,
        default=8080,
        help="Weaviate port (default: 8080)"
    )
    parser.add_argument(
        "--pgvector-container",
        default="pgvector",
        help="pgvector Docker container name (default: pgvector)"
    )
    parser.add_argument(
        "--pgvector-db",
        default="vectordb",
        help="pgvector database name (default: vectordb)"
    )
    parser.add_argument(
        "--no-gate",
        action="store_true",
        help="Disable gate filtering"
    )
    parser.add_argument(
        "--no-oracle",
        action="store_true",
        help="Disable oracle execution"
    )
    parser.add_argument(
        "--naive-triage",
        action="store_true",
        help="Use naive triage classification"
    )
    parser.add_argument(
        "--run-tag",
        required=True,
        help="Required run tag"
    )
    parser.add_argument(
        "--output-dir",
        default="runs",
        help="Output directory (default: runs)"
    )
    parser.add_argument(
        "--require-real",
        action="store_true",
        help="Require real Milvus connection"
    )
    parser.add_argument(
        "--templates",
        default="casegen/templates/test_phase5_comprehensive.yaml",
        help="Test template file(s) to use (default: test_phase5_comprehensive.yaml)"
    )
    parser.add_argument(
        "--diagnostic-quality",
        default="full",
        choices=["full", "partial", "none"],
        help="Mock adapter diagnostic quality (default: full)"
    )
    parser.add_argument(
        "--response-mode",
        default="success",
        choices=["success", "failure"],
        help="Mock adapter response mode (default: success)"
    )

    args = parser.parse_args()

    # Create variant flags
    variant_flags = VariantFlags(
        no_gate=args.no_gate,
        no_oracle=args.no_oracle,
        naive_triage=args.naive_triage
    )

    # Generate run ID
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"phase5.3-{args.run_tag}-{timestamp}"

    print(f"=== Phase 5.3 Evaluation Runner ===")
    print(f"Run ID: {run_id}")
    print(f"Run Tag: {args.run_tag}")
    print(f"Output: {args.output_dir}/{run_id}")
    print()

    # Display variant configuration
    print("Variant Configuration:")
    print(f"  Adapter: {args.adapter}")
    if args.adapter == "mock":
        print(f"  Response Mode: {args.response_mode}")
        print(f"  Diagnostic Quality: {args.diagnostic_quality}")
    print(f"  Gate Filtering: {'DISABLED' if variant_flags.no_gate else 'ENABLED'}")
    print(f"  Oracle Execution: {'DISABLED' if variant_flags.no_oracle else 'ENABLED'}")
    print(f"  Triage Mode: {'naive' if variant_flags.naive_triage else 'diagnostic'}")
    print()

    # Load contract and profile
    print("Loading contract and profile...")
    contract = get_default_contract()
    profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
    print(f"Contract: {len(contract.operations)} operations")
    print(f"Profile: {len(profile.supported_operations)} supported operations")
    print()

    # Create adapter with fallback
    adapter, adapter_flags, adapter_info = create_adapter_with_fallback(
        args.adapter, args.host, args.port, args.require_real, args.diagnostic_quality, args.response_mode,
        qdrant_url=args.qdrant_url,
        weaviate_host=args.weaviate_host,
        weaviate_port=args.weaviate_port,
        pgvector_container=args.pgvector_container,
        pgvector_db=args.pgvector_db,
    )

    variant_flags.adapter_fallback = adapter_flags.adapter_fallback
    variant_flags.adapter_fallback_reason = adapter_flags.adapter_fallback_reason

    # Capture fingerprint if using Milvus
    fingerprint = None
    if args.adapter == "milvus" and not variant_flags.adapter_fallback:
        try:
            connection_config = {
                "host": args.host,
                "port": args.port,
                "alias": "default"
            }
            fingerprint = capture_environment(connection_config, adapter)
            print(f"Connected to Milvus {fingerprint.milvus_version}")
        except Exception as e:
            print(f"WARNING: Could not capture fingerprint: {e}")
    else:
        print(f"Using {adapter_info['adapter_actual']} adapter")
    print()

    # Create executor with oracles
    # Set up runtime context with test collection for Type-4 tests
    runtime_context = {
        "collections": ["test_collection"],
        "indexed_collections": ["test_collection"],
        "loaded_collections": ["test_collection"],
        "connected": True,
        "target_collection": "test_collection",
        "supported_features": ["IVF_FLAT", "HNSW"]
    }

    precond = PreconditionEvaluator(contract, profile, runtime_context)
    oracles = create_oracles(variant_flags)
    executor = Executor(adapter, precond, oracles)
    executor.variant_flags = variant_flags.to_dict()

    triage = Triage()
    writer = EvidenceWriter()

    # Load test cases from specified templates
    print("Loading test cases...")
    template_files = args.templates.split(",") if "," in args.templates else [args.templates]
    all_templates = []
    for template_file in template_files:
        print(f"  Loading: {template_file}")
        templates = load_templates(template_file.strip())
        all_templates.extend(templates)
    cases = instantiate_all(all_templates, {"collection": "test_collection"})
    print(f"Loaded {len(cases)} cases from {len(template_files)} template file(s)")
    print()

    # Load runtime snapshot if Milvus
    runtime_snapshots = []
    if args.adapter == "milvus" and not variant_flags.adapter_fallback:
        try:
            snapshot = adapter.get_runtime_snapshot()
            snapshot_id = f"snapshot-{datetime.now().strftime('%H%M%S')}"
            snapshot["snapshot_id"] = snapshot_id
            snapshot["timestamp"] = datetime.now().isoformat()
            runtime_snapshots.append(snapshot)
            precond.load_runtime_snapshot(snapshot)
            print(f"Runtime snapshot: {len(snapshot['collections'])} collections")
        except Exception as e:
            print(f"WARNING: Could not load runtime snapshot: {e}")
    print()

    # Execute cases
    print("Executing cases...")
    results = []
    for case in cases:
        print(f"  Executing: {case.case_id} ({case.operation})")
        result = executor.execute_case(case, run_id)
        results.append(result)

    print(f"Executed {len(results)} cases")
    success_count = sum(1 for r in results if r.observed_outcome == ObservedOutcome.SUCCESS)
    failure_count = sum(1 for r in results if r.observed_outcome == ObservedOutcome.FAILURE)
    print(f"  Success: {success_count}")
    print(f"  Failure: {failure_count}")
    print()

    # Classify bugs
    print("Classifying bugs...")
    triage_results = []
    for case in cases:
        result = next((r for r in results if r.case_id == case.case_id), None)
        if result:
            naive = variant_flags.naive_triage
            triage_result = triage.classify(case, result, naive=naive)
            triage_results.append(triage_result)

    bug_count = sum(1 for t in triage_results if t is not None)
    print(f"Found {bug_count} bugs")
    print()

    # Write evidence
    print("Writing evidence...")
    run_dir = writer.create_run_dir(run_id, base_path=args.output_dir)
    run_metadata = {
        "run_id": run_id,
        "run_tag": args.run_tag,
        "timestamp": datetime.now().isoformat(),
        "phase": "5.3",
        "adapter": args.adapter,
        "adapter_requested": adapter_info["adapter_requested"],
        "adapter_actual": adapter_info["adapter_actual"],
        "adapter_fallback": adapter_info["adapter_fallback"],
        "fallback_reason": adapter_info["fallback_reason"],
        "response_mode": args.response_mode,
        "diagnostic_quality": args.diagnostic_quality,
        "variant_flags": variant_flags.to_dict(),
        "templates": args.templates,
        "case_count": len(cases),
        "bug_count": bug_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "runtime_context": runtime_context
    }

    if fingerprint:
        run_metadata["fingerprint"] = fingerprint.model_dump(mode="json")

    writer.write_all(
        run_dir,
        run_metadata,
        cases,
        results,
        triage_results,
        fingerprint,
        runtime_snapshots if (args.adapter == "milvus" and not variant_flags.adapter_fallback) else None
    )
    print(f"Evidence written to {run_dir}")
    print()

    # Summary
    print("=== Summary ===")
    print(f"Run Tag: {args.run_tag}")
    print(f"Adapter: {args.adapter}")
    if variant_flags.adapter_fallback:
        print(f"ADAPTER FALLBACK: {variant_flags.adapter_fallback_reason}")
    print(f"Total cases: {len(cases)}")
    print(f"Bugs found: {bug_count}")
    print(f"Gate filtering: {'OFF' if variant_flags.no_gate else 'ON'}")
    print(f"Oracle execution: {'OFF' if variant_flags.no_oracle else 'ON'}")
    print(f"Triage mode: {'naive' if variant_flags.naive_triage else 'diagnostic'}")
    print(f"Evidence: {run_dir}")
    print()

    # Cleanup
    if args.adapter == "milvus" and not variant_flags.adapter_fallback:
        try:
            adapter.close()
            print("Milvus connection closed")
        except Exception:
            pass

    print("Done!")


if __name__ == "__main__":
    main()
