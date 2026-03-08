"""Cross-database differential comparison - wraps existing logic."""

from pathlib import Path
from datetime import datetime
import json
import yaml

from schemas.case import TestCase
from ai_db_qa.workflows.validate import _create_adapter, _save_results


def run_compare(args):
    """Execute comparison workflow."""
    config = _load_compare_config(args)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = config.get('tag', 'comparison')
    output_base = Path(config.get('output_dir', 'results')) / f"differential_{tag}_{timestamp}"
    output_base.mkdir(parents=True, exist_ok=True)

    # Load cases
    with open(config['pack_path'], 'r') as f:
        pack_data = json.load(f)
    cases = [TestCase(**c) for c in pack_data['cases']]

    # Run on each database (reuse validate logic)
    results_by_db = {}
    adapters_used = []
    for db_config in config['databases']:
        db_type = db_config['type']
        db_output = output_base / db_type
        db_output.mkdir(exist_ok=True)

        print(f"\n{'='*60}\n  Running on {db_type}\n{'='*60}")
        adapter, results = _run_db_validation(db_config, cases, db_output, f"{tag}_{timestamp}")
        results_by_db[db_type] = results
        adapters_used.append(type(adapter).__name__)

    # Analyze differential
    print(f"\n[Compare] Analyzing differential...")
    diff_details = _analyze_differential(results_by_db, cases)

    # Save differential artifacts
    _save_differential_artifacts(diff_details, output_base, tag, timestamp, config, adapters_used)

    print(f"\n[Compare] Comparison complete! Results: {output_base}")


def _load_compare_config(args) -> dict:
    if args.campaign:
        with open(args.campaign, 'r') as f:
            c = yaml.safe_load(f)
        return {
            'databases': c['databases'],
            'pack_path': Path(c['case_pack']),
            'tag': c.get('tag'),
            'output_dir': args.output,
            '_campaign_path': str(args.campaign)  # Store for metadata
        }
    dbs = args.databases.split(',')
    return {
        'databases': [{'type': d.strip(), 'host': 'localhost', 'port': 19530 if d.strip() == 'milvus' else 2881, 'alias': d.strip()} for d in dbs],
        'pack_path': args.pack,
        'tag': args.tag,
        'output_dir': args.output,
        '_campaign_path': 'cli_args'
    }


def _run_db_validation(db_config, cases, output_dir, run_id):
    """Run validation on single DB - reuses validate workflow logic."""
    from contracts.core.loader import get_default_contract
    from contracts.db_profiles.loader import load_profile
    from pipeline.executor import Executor
    from pipeline.preconditions import PreconditionEvaluator
    from pipeline.triage import Triage
    from oracles.write_read_consistency import WriteReadConsistency
    from oracles.filter_strictness import FilterStrictness
    from oracles.monotonicity import Monotonicity

    adapter = _create_adapter(db_config['type'], db_config)
    snapshot = adapter.get_runtime_snapshot()

    contract = get_default_contract()
    profile = load_profile(f"contracts/db_profiles/{db_config['type']}_profile.yaml")

    precond = PreconditionEvaluator(contract, profile, {
        "collections": snapshot.get("collections", []),
        "indexed_collections": snapshot.get("indexed_collections", []),
        "loaded_collections": snapshot.get("loaded_collections", []),
        "connected": snapshot.get("connected", True),
        "supported_features": ["hybrid_search", "filtering", "multi_model"]
    })
    precond.load_runtime_snapshot(snapshot)

    oracles = [WriteReadConsistency(validate_ids=True), FilterStrictness(), Monotonicity()]
    executor = Executor(adapter, precond, oracles)
    triage = Triage()

    results = []
    for case in cases:
        result = executor.execute_case(case, run_id)
        result.triage_result = triage.classify(case, result, naive=False)
        results.append(result)

    config_source = "compare_workflow"  # compare workflow context
    _save_results(results, cases, output_dir, db_config['type'], run_id, adapter, config_source)
    return adapter, results


def _analyze_differential(results_by_db: dict, cases) -> dict:
    """Analyze differences - reuses existing differential-label logic.

    MILESTONE-1 NOTE: This imports from scripts/analyze_differential_results.py.
    This is temporary technical debt. Future milestone should extract
    reusable differential functions into a neutral module (e.g., analysis/differential.py).
    """
    db_names = list(results_by_db.keys())
    if len(db_names) != 2:
        return {'total_cases': len(cases), 'genuine_difference_count': 0, 'stricter_db': 'none', 'genuine_differences': []}

    # Import existing differential analysis logic (MILESTONE-1 TEMPORARY)
    from scripts.analyze_differential_results import (
        compare_outcomes, label_differences, identify_stricter_database
    )

    r1 = {r.case_id: r for r in results_by_db[db_names[0]]}
    r2 = {r.case_id: r for r in results_by_db[db_names[1]]}

    # Use existing comparison logic
    diffs = []
    milvus_strict_count = 0
    seekdb_strict_count = 0

    for case in cases:
        res1, res2 = r1.get(case.case_id), r2.get(case.case_id)
        if not res1 or not res2:
            continue

        # Reuse existing label_differences logic
        label = label_differences(res1, res2, case)
        if label != 'no_difference':
            diffs.append({
                'case_id': case.case_id,
                'difference_type': label,
                f'{db_names[0]}_outcome': res1.observed_outcome.value,
                f'{db_names[1]}_outcome': res2.observed_outcome.value,
                'interpretation': _interpret_label(label, db_names)
            })

            # Track stricter database
            if label == 'db1_stricter':
                if db_names[0] == 'milvus':
                    milvus_strict_count += 1
                else:
                    seekdb_strict_count += 1
            elif label == 'db2_stricter':
                if db_names[1] == 'milvus':
                    milvus_strict_count += 1
                else:
                    seekdb_strict_count += 1

    # Determine stricter database
    stricter_db = identify_stricter_database(milvus_strict_count, seekdb_strict_count)

    return {
        'total_cases': len(cases),
        'genuine_difference_count': len(diffs),
        'stricter_db': stricter_db,
        'genuine_differences': diffs,
        'milvus_strict_count': milvus_strict_count,
        'seekdb_strict_count': seekdb_strict_count
    }


def _interpret_label(label: str, db_names: list) -> str:
    """Convert difference label to human-readable interpretation."""
    if label == 'db1_stricter':
        return f"{db_names[0].capitalize()} rejects, {db_names[1].capitalize()} accepts (stricter)"
    elif label == 'db2_stricter':
        return f"{db_names[1].capitalize()} rejects, {db_names[0].capitalize()} accepts (stricter)"
    elif 'oracle' in label.lower():
        return f"Different oracle results"
    return label.replace('_', ' ').title()


def _save_differential_artifacts(details: dict, output_dir: Path, tag: str, timestamp: str, config: dict, adapters: list):
    """Save differential artifacts."""
    with open(output_dir / "differential_details.json", "w") as f:
        json.dump(details, f, indent=2, default=str)

    # Generate report
    lines = [
        f"# Differential Comparison\n\n**Tag**: {tag}\n**Timestamp**: {timestamp}\n\n",
        f"## Summary\n- Total: {details['total_cases']}\n- Differences: {details['genuine_difference_count']}\n- Stricter DB: {details.get('stricter_db', 'none')}\n\n"
    ]
    for d in details['genuine_differences']:
        lines.append(f"### {d['case_id']}\n**Type**: {d['difference_type']}\n**Interpretation**: {d['interpretation']}\n\n")
    (output_dir / "differential_report.md").write_text(''.join(lines))

    metadata = {
        "tool_version": "0.1.0",
        "workflow_type": "compare",
        "databases": config['databases'],
        "adapter_used": adapters,
        "config_source": str(config.get('_campaign_path', 'cli_args')),
        "timestamp": timestamp,
        "run_tag": tag
    }
    with open(output_dir / "comparison_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"[Compare] Saved differential artifacts")
