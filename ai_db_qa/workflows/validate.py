"""Single-database validation workflow."""

from pathlib import Path
from datetime import datetime
import json
import yaml

from adapters.milvus_adapter import MilvusAdapter
from adapters.seekdb_adapter import SeekDBAdapter
from pipeline.executor import Executor
from pipeline.preconditions import PreconditionEvaluator
from pipeline.triage import Triage
from oracles.write_read_consistency import WriteReadConsistency
from oracles.filter_strictness import FilterStrictness
from oracles.monotonicity import Monotonicity
from contracts.core.loader import get_default_contract
from contracts.db_profiles.loader import load_profile
from schemas.case import TestCase


def run_validate(args):
    """Execute validation workflow."""
    config = _load_validate_config(args)

    print(f"[Validate] Connecting to {config['db_type']}...")
    adapter = _create_adapter(config['db_type'], config['db_config'])
    snapshot = adapter.get_runtime_snapshot()

    contract = get_default_contract()
    profile = load_profile(
        config.get('profile_path') or
        f"contracts/db_profiles/{config['db_type']}_profile.yaml"
    )

    # Derive runtime context from snapshot (no hardcoded feature list)
    runtime_context = {
        "collections": snapshot.get("collections", []),
        "indexed_collections": snapshot.get("indexed_collections", []),
        "loaded_collections": snapshot.get("loaded_collections", []),
        "connected": snapshot.get("connected", True),
        # Derive from profile/adapter if available, otherwise empty set
        "supported_features": snapshot.get("supported_features", profile.get("supported_features", []))
    }

    precond = PreconditionEvaluator(contract, profile, runtime_context)
    precond.load_runtime_snapshot(snapshot)

    oracles = [WriteReadConsistency(validate_ids=True), FilterStrictness(), Monotonicity()]
    executor = Executor(adapter, precond, oracles)
    triage = Triage()

    print(f"[Validate] Loading cases from {config['pack_path']}...")
    with open(config['pack_path'], 'r') as f:
        pack_data = json.load(f)
    cases = [TestCase(**c) for c in pack_data['cases']]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = Path(config.get('output_dir', 'results')) / f"{config['db_type']}_validation_{timestamp}"
    output_base.mkdir(parents=True, exist_ok=True)

    print(f"[Validate] Running {len(cases)} cases...")
    results = []
    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {case.case_id}...", end=' ')
        result = executor.execute_case(case, f"validation_{timestamp}")
        triage_result = triage.classify(case, result, naive=False)
        result.triage_result = triage_result
        results.append(result)
        print(f"{result.observed_outcome.value}")

    config_source = str(args.campaign) if args.campaign else "cli_args"
    _save_results(results, cases, output_base, config['db_type'], timestamp, adapter, config_source)

    print(f"[Validate] Validation complete! Results: {output_base}")


def _load_validate_config(args) -> dict:
    if args.campaign:
        with open(args.campaign, 'r') as f:
            campaign = yaml.safe_load(f)
        db = campaign['databases'][0]
        return {
            'db_type': db['type'],
            'db_config': {
                'host': args.host or db.get('host', 'localhost'),
                'port': args.port or db.get('port', 19530 if db['type'] == 'milvus' else 2881),
                'alias': db.get('alias', 'default')
            },
            'pack_path': Path(campaign['case_pack']),
            'profile_path': Path(campaign.get('contract', {}).get('profile')) if campaign.get('contract') else None,
            'output_dir': args.output
        }
    else:
        return {
            'db_type': args.db,
            'db_config': {'host': args.host or 'localhost', 'port': args.port or 19530, 'alias': 'default'},
            'pack_path': args.pack,
            'profile_path': args.contract,
            'output_dir': args.output
        }


def _create_adapter(db_type: str, db_config: dict):
    config = {**db_config, 'type': db_type}
    if db_type == 'milvus':
        return MilvusAdapter(config)
    return SeekDBAdapter(config)


def _save_results(results, cases, output_dir: Path, db_type: str, timestamp: str, adapter, config_source: str):
    """Save all output artifacts following explicit contracts."""

    # 1. execution_results.jsonl - ALL cases, triage_result included (may be null)
    with open(output_dir / "execution_results.jsonl", "w") as f:
        for result in results:
            d = result.__dict__.copy()
            d['triage_result'] = result.triage_result.__dict__ if result.triage_result else None
            f.write(json.dumps(d, default=str) + "\n")

    # 2. triage_results.json - ONLY bugs (taxonomy-aware filtering)
    # Exclude type-2.precondition_failed (expected behavior, not a bug)
    bug_types_to_include = {"type-1", "type-2", "type-3", "type-4"}
    bugs = [
        r.triage_result.__dict__
        for r in results
        if r.triage_result is not None
        and r.triage_result.final_type.value in bug_types_to_include
    ]
    with open(output_dir / "triage_results.json", "w") as f:
        json.dump(bugs, f, indent=2)

    # 3. cases.jsonl - original cases
    with open(output_dir / "cases.jsonl", "w") as f:
        for case in cases:
            f.write(json.dumps(case.__dict__, default=str) + "\n")

    # 4. summary.json - with minimum required fields and correct accounting
    bug_counts = {}
    for b in bugs:
        bt = b.get('final_type', 'unknown')
        bug_counts[bt] = bug_counts.get(bt, 0) + 1

    precondition_filtered = sum(1 for r in results if not r.precondition_pass)
    total_bugs = len(bugs)
    ran_successfully = sum(1 for r in results if r.precondition_pass)

    # Tightened accounting: non_bugs are explicitly defined
    # non_bugs = executed cases (precondition_pass=true) with no bug-classifying triage result
    # A triage_result that is None, or is type-2.precondition_failed, means "not a bug"
    non_bugs = sum(
        1 for r in results
        if r.precondition_pass and (
            r.triage_result is None or
            r.triage_result.final_type.value == "type-2.precondition_failed"
        )
    )

    summary = {
        "run_id": f"{db_type}_validation_{timestamp}",
        "run_tag": "validation",
        "db_type": db_type,
        "timestamp": timestamp,
        "total_cases": len(cases),
        "total_executed": ran_successfully + precondition_filtered,
        "bug_candidate_counts_by_type": bug_counts,
        "total_bugs": total_bugs,
        "precondition_filtered_count": precondition_filtered,
        "non_bug_count": non_bugs
    }
    with open(output_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # 5. metadata.json - with required convention 1 fields
    metadata = {
        "tool_version": "0.1.0",
        "workflow_type": "validate",
        "db_type": db_type,
        "adapter_used": type(adapter).__name__,
        "config_source": config_source,
        "timestamp": timestamp,
        "run_tag": "validation"
    }
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"[Validate] Saved: execution_results.jsonl ({len(results)}), triage_results.json ({len(bugs)} bugs)")


# Export for use by compare workflow
__all__ = ['run_validate', '_create_adapter', '_save_results']
