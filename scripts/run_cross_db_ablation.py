"""Cross-database ablation experiment runner.

This script runs Phase 5.3 evaluation across multiple databases (Qdrant, Weaviate, pgvector)
to demonstrate ablation effects on different database backends.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.run_phase5_3_eval import (
    create_adapter_with_fallback,
    create_oracles,
    VariantFlags
)
from casegen.generators.instantiator import load_templates, instantiate_all
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from pipeline.preconditions import PreconditionEvaluator
from pipeline.executor import Executor
from pipeline.triage import Triage
from evidence.writer import EvidenceWriter
from schemas.common import ObservedOutcome


# Database configurations
DB_CONFIGS = {
    "mock": {
        "profile": "contracts/db_profiles/milvus_profile.yaml",
        "adapter": "mock",
        "mock": True
    },
    "qdrant": {
        "profile": "contracts/db_profiles/qdrant_profile.yaml",
        "adapter": "qdrant",
        "default_url": "http://localhost:6333"
    },
    "weaviate": {
        "profile": "contracts/db_profiles/weaviate_profile.yaml", 
        "adapter": "weaviate",
        "default_host": "localhost",
        "default_port": 8080
    },
    "pgvector": {
        "profile": "contracts/db_profiles/pgvector_profile.yaml",
        "adapter": "pgvector",
        "default_container": "pgvector",
        "default_db": "vectordb"
    },
    "milvus": {
        "profile": "contracts/db_profiles/milvus_profile.yaml",
        "adapter": "milvus",
        "default_host": "localhost",
        "default_port": 19530
    }
}


def run_single_db_experiment(
    db_name: str,
    templates: str,
    variant_flags: VariantFlags,
    run_tag: str,
    output_dir: str,
    require_real: bool = False,
    **adapter_kwargs
) -> Dict[str, Any]:
    """Run experiment on a single database.
    
    Args:
        db_name: Database name (qdrant, weaviate, pgvector, milvus)
        templates: Template file path(s)
        variant_flags: Experiment variant flags
        run_tag: Run identifier tag
        output_dir: Output directory
        require_real: Require real database connection
        **adapter_kwargs: Additional adapter connection parameters
        
    Returns:
        Dictionary with experiment results and metadata
    """
    print(f"\n{'='*60}")
    print(f"Running experiment on: {db_name.upper()}")
    print(f"{'='*60}")
    
    db_config = DB_CONFIGS.get(db_name)
    if not db_config:
        return {"error": f"Unknown database: {db_name}"}
    
    # Generate run ID
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"cross-db-{db_name}-{run_tag}-{timestamp}"
    
    # Create adapter with fallback
    adapter, adapter_flags, adapter_info = create_adapter_with_fallback(
        db_config["adapter"],
        adapter_kwargs.get("host", db_config.get("default_host", "localhost")),
        adapter_kwargs.get("port", db_config.get("default_port", 19530)),
        require_real=require_real,
        qdrant_url=adapter_kwargs.get("qdrant_url", db_config.get("default_url", "http://localhost:6333")),
        weaviate_host=adapter_kwargs.get("weaviate_host", db_config.get("default_host", "localhost")),
        weaviate_port=adapter_kwargs.get("weaviate_port", db_config.get("default_port", 8080)),
        pgvector_container=adapter_kwargs.get("pgvector_container", db_config.get("default_container", "pgvector")),
        pgvector_db=adapter_kwargs.get("pgvector_db", db_config.get("default_db", "vectordb")),
    )
    
    if adapter_info.get("adapter_fallback") and require_real:
        return {"error": f"Failed to connect to {db_name}", "fallback_reason": adapter_info.get("fallback_reason")}
    
    # Load contract and profile
    try:
        contract = get_default_contract()
        profile = load_profile(db_config["profile"])
    except Exception as e:
        return {"error": f"Failed to load contract/profile: {e}"}
    
    # Set up runtime context
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
    
    # Load test cases
    try:
        template_files = templates.split(",") if "," in templates else [templates]
        all_templates = []
        for template_file in template_files:
            loaded = load_templates(template_file.strip())
            all_templates.extend(loaded)
        cases = instantiate_all(all_templates, {"collection": "test_collection"})
    except Exception as e:
        return {"error": f"Failed to load templates: {e}"}
    
    # Execute cases
    print(f"Executing {len(cases)} test cases...")
    results = []
    for case in cases:
        result = executor.execute_case(case, run_id)
        results.append(result)
    
    success_count = sum(1 for r in results if r.observed_outcome == ObservedOutcome.SUCCESS)
    failure_count = sum(1 for r in results if r.observed_outcome == ObservedOutcome.FAILURE)
    
    # Classify bugs
    triage_results = []
    for case in cases:
        result = next((r for r in results if r.case_id == case.case_id), None)
        if result:
            triage_result = triage.classify(case, result, naive=variant_flags.naive_triage)
            triage_results.append(triage_result)
    
    bug_count = sum(1 for t in triage_results if t is not None)
    
    # Write evidence
    run_dir = writer.create_run_dir(run_id, base_path=output_dir)
    run_metadata = {
        "run_id": run_id,
        "run_tag": run_tag,
        "timestamp": datetime.now().isoformat(),
        "phase": "cross-db-ablation",
        "database": db_name,
        "adapter_info": adapter_info,
        "variant_flags": variant_flags.to_dict(),
        "templates": templates,
        "case_count": len(cases),
        "bug_count": bug_count,
        "success_count": success_count,
        "failure_count": failure_count,
    }
    
    writer.write_all(run_dir, run_metadata, cases, results, triage_results, None, None)
    
    # Cleanup
    try:
        adapter.close()
    except Exception:
        pass
    
    return {
        "database": db_name,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "case_count": len(cases),
        "bug_count": bug_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "adapter_fallback": adapter_info.get("adapter_fallback", False),
        "fallback_reason": adapter_info.get("fallback_reason")
    }


def run_cross_db_ablation(
    databases: List[str],
    templates: str,
    run_tag: str,
    output_dir: str,
    require_real: bool = False,
    no_gate: bool = False,
    no_oracle: bool = False,
    naive_triage: bool = False,
    **adapter_kwargs
) -> Dict[str, Any]:
    """Run ablation experiments across multiple databases.
    
    Args:
        databases: List of database names to test
        templates: Template file path(s)
        run_tag: Run identifier tag
        output_dir: Output directory
        require_real: Require real database connections
        no_gate: Disable gate filtering
        no_oracle: Disable oracle execution
        naive_triage: Use naive triage classification
        **adapter_kwargs: Additional adapter connection parameters
        
    Returns:
        Dictionary with aggregated results from all databases
    """
    variant_flags = VariantFlags(
        no_gate=no_gate,
        no_oracle=no_oracle,
        naive_triage=naive_triage
    )
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "run_tag": run_tag,
        "variant_flags": variant_flags.to_dict(),
        "databases_tested": [],
        "databases_failed": [],
        "summary": {}
    }
    
    for db_name in databases:
        print(f"\n[Cross-DB Ablation] Testing {db_name}...")
        
        result = run_single_db_experiment(
            db_name=db_name,
            templates=templates,
            variant_flags=variant_flags,
            run_tag=run_tag,
            output_dir=output_dir,
            require_real=require_real,
            **adapter_kwargs
        )
        
        if "error" in result:
            print(f"  ERROR: {result['error']}")
            results["databases_failed"].append({
                "database": db_name,
                "error": result["error"],
                "fallback_reason": result.get("fallback_reason")
            })
        else:
            print(f"  Cases: {result['case_count']}, Bugs: {result['bug_count']}")
            results["databases_tested"].append(result)
    
    # Generate summary
    total_cases = sum(r["case_count"] for r in results["databases_tested"])
    total_bugs = sum(r["bug_count"] for r in results["databases_tested"])
    
    results["summary"] = {
        "total_databases": len(databases),
        "successful_databases": len(results["databases_tested"]),
        "failed_databases": len(results["databases_failed"]),
        "total_cases": total_cases,
        "total_bugs": total_bugs,
        "bug_rate": total_bugs / total_cases if total_cases > 0 else 0
    }
    
    # Write aggregated report
    report_path = Path(output_dir) / f"cross-db-ablation-{run_tag}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'='*60}")
    print("Cross-Database Ablation Summary")
    print(f"{'='*60}")
    print(f"Databases tested: {results['summary']['successful_databases']}/{results['summary']['total_databases']}")
    print(f"Total cases: {total_cases}")
    print(f"Total bugs found: {total_bugs}")
    print(f"Overall bug rate: {results['summary']['bug_rate']:.2%}")
    print(f"Report saved: {report_path}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run cross-database ablation experiments"
    )
    parser.add_argument(
        "--databases",
        default="qdrant,weaviate,pgvector",
        help="Comma-separated list of databases to test (default: qdrant,weaviate,pgvector)"
    )
    parser.add_argument(
        "--templates",
        default="casegen/templates/experimental_triage.yaml",
        help="Test template file(s) to use"
    )
    parser.add_argument(
        "--run-tag",
        required=True,
        help="Required run tag"
    )
    parser.add_argument(
        "--output-dir",
        default="runs/cross_db_ablation",
        help="Output directory (default: runs/cross_db_ablation)"
    )
    parser.add_argument(
        "--require-real",
        action="store_true",
        help="Require real database connections (fail if unavailable)"
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
        "--qdrant-url",
        default="http://localhost:6333",
        help="Qdrant URL"
    )
    parser.add_argument(
        "--weaviate-host",
        default="localhost",
        help="Weaviate host"
    )
    parser.add_argument(
        "--weaviate-port",
        type=int,
        default=8080,
        help="Weaviate port"
    )
    parser.add_argument(
        "--pgvector-container",
        default="pgvector",
        help="pgvector Docker container name"
    )
    parser.add_argument(
        "--pgvector-db",
        default="vectordb",
        help="pgvector database name"
    )
    
    args = parser.parse_args()
    
    databases = [db.strip() for db in args.databases.split(",")]
    
    run_cross_db_ablation(
        databases=databases,
        templates=args.templates,
        run_tag=args.run_tag,
        output_dir=args.output_dir,
        require_real=args.require_real,
        no_gate=args.no_gate,
        no_oracle=args.no_oracle,
        naive_triage=args.naive_triage,
        qdrant_url=args.qdrant_url,
        weaviate_host=args.weaviate_host,
        weaviate_port=args.weaviate_port,
        pgvector_container=args.pgvector_container,
        pgvector_db=args.pgvector_db
    )


if __name__ == "__main__":
    main()
