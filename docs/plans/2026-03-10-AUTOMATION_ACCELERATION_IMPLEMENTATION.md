# Automation Acceleration MVP - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build campaign bootstrapping infrastructure to reduce new campaign startup cost by 50-70%.

**Architecture:** Four-component system:
- P1: Declarative capability registry (static scan + manual tuning)
- P2: Contract coverage index (immutable contracts + dynamic status)
- P3: Campaign bootstrap scaffold (YAML config → 8 artifacts)
- P4: Results index/diff (manual, explicit comparison)

**Tech Stack:** Python 3.10+, JSON schemas, argparse, pathlib

---

## Task 1: Create P1 Capability Registry Structure

**Files:**
- Create: `capabilities/README.md`
- Create: `capabilities/.gitkeep`
- Create: `scripts/bootstrap_capability_registry.py`

**Step 1: Create capabilities directory structure**

```bash
mkdir -p capabilities
touch capabilities/.gitkeep
```

**Step 2: Create capabilities README**

```markdown
# Capability Registry

This directory contains capability declarations for each database adapter.

## Files

- `milvus_capabilities.json` - Milvus adapter capabilities
- `qdrant_capabilities.json` - Qdrant adapter capabilities
- `seekdb_capabilities.json` - SeekDB adapter capabilities
- `mock_capabilities.json` - Mock adapter capabilities

## Schema

See `docs/plans/2026-03-10-AUTOMATION_ACCELERATION_MVP.md` for full schema.

## Updating

Run `python scripts/bootstrap_capability_registry.py` to regenerate from adapter code.
```

**Step 3: Commit**

```bash
git add capabilities/ capabilities/README.md capabilities/.gitkeep
git commit -m "feat(automation): create capability registry directory structure"
```

---

## Task 2: Implement Capability Registry Bootstrap Script

**Files:**
- Create: `scripts/bootstrap_capability_registry.py`

**Step 1: Write bootstrap script skeleton**

```python
#!/usr/bin/env python3
"""Bootstrap capability registry from adapter code.

Scans adapter implementations to extract supported operations.
Generates initial capability JSON files for manual review.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Any


class CapabilityScanner:
    """Scan adapter code to extract operations."""

    def __init__(self, adapter_path: Path):
        self.adapter_path = adapter_path

    def scan(self) -> List[Dict[str, Any]]:
        """Scan adapter file for operation methods.

        Returns:
            List of operation dicts with name and implementation_path
        """
        operations = []
        content = self.adapter_path.read_text()

        # Find _operation methods (e.g., _create_collection, _insert, _search)
        pattern = r'def (_\w+)\(self[^)]*\):'
        for match in re.finditer(pattern, content):
            method_name = match.group(1)
            operations.append({
                "operation": method_name.lstrip("_"),
                "support_status": "unknown",
                "support_level": "static_only",
                "confidence": "low",
                "implementation_path": f"{self.adapter_path.stem}Adapter.{method_name}",
                "verification_path": None,
                "known_constraints": [],
                "evidence_source": "static_scan",
                "validated_in_campaigns": [],
                "notes": "TODO: Manual review required"
            })

        return operations


def main():
    parser = argparse.ArgumentParser(description="Bootstrap capability registry")
    parser.add_argument("--adapter", required=True, help="Adapter name (milvus, qdrant, seekdb, mock)")
    parser.add_argument("--output", default="capabilities", help="Output directory")
    args = parser.parse_args()

    # Map adapter name to file path
    adapter_files = {
        "milvus": "adapters/milvus_adapter.py",
        "qdrant": "adapters/qdrant_adapter.py",
        "seekdb": "adapters/seekdb_adapter.py",
        "mock": "adapters/mock.py"
    }

    if args.adapter not in adapter_files:
        print(f"Error: Unknown adapter '{args.adapter}'")
        print(f"Available: {', '.join(adapter_files.keys())}")
        return 1

    adapter_path = Path(adapter_files[args.adapter])
    if not adapter_path.exists():
        print(f"Error: Adapter file not found: {adapter_path}")
        return 1

    # Scan adapter
    scanner = CapabilityScanner(adapter_path)
    operations = scanner.scan()

    # Build registry
    registry = {
        "adapter_name": f"{args.adapter}_adapter",
        "db_family": args.adapter.capitalize(),
        "sdk_version": "TODO",
        "validated_db_version": "TODO",
        "last_updated": "2026-03-10",
        "operations": operations
    }

    # Write output
    output_path = Path(args.output) / f"{args.adapter}_capabilities.json"
    output_path.write_text(json.dumps(registry, indent=2))
    print(f"Generated: {output_path}")
    print(f"Found {len(operations)} operations")
    print("Please review and update: support_status, confidence, notes")

    return 0


if __name__ == "__main__":
    exit(main())
```

**Step 2: Commit**

```bash
git add scripts/bootstrap_capability_registry.py
git commit -m "feat(automation): add capability registry bootstrap script"
```

---

## Task 3: Generate Initial Capability Registries

**Files:**
- Create: `capabilities/milvus_capabilities.json`
- Create: `capabilities/qdrant_capabilities.json`
- Create: `capabilities/seekdb_capabilities.json`
- Create: `capabilities/mock_capabilities.json`

**Step 1: Generate Milvus capabilities**

```bash
python scripts/bootstrap_capability_registry.py --adapter milvus
```

**Step 2: Generate Qdrant capabilities**

```bash
python scripts/bootstrap_capability_registry.py --adapter qdrant
```

**Step 3: Generate SeekDB capabilities**

```bash
python scripts/bootstrap_capability_registry.py --adapter seekdb
```

**Step 4: Generate Mock capabilities**

```bash
python scripts/bootstrap_capability_registry.py --adapter mock
```

**Step 5: Review and update key fields**

Edit each file to update:
- `sdk_version`: Check actual version
- `support_status`: Change unknown → supported/unsupported/partially_supported
- `confidence`: Set high/medium/low
- `known_constraints`: Add known limitations
- `validated_in_campaigns`: Add campaign names if validated
- `notes`: Add context

**Step 6: Commit**

```bash
git add capabilities/*.json
git commit -m "feat(automation): add initial capability registries for all adapters"
```

---

## Task 4: Create P2 Contract Coverage Index Structure

**Files:**
- Create: `contracts/CONTRACT_COVERAGE_INDEX.json`
- Create: `contracts/VALIDATION_MATRIX.json`

**Step 1: Create initial coverage index template**

```python
#!/usr/bin/env python3
"""Generate contract coverage index from existing contracts and results."""

import json
from pathlib import Path
from typing import Dict, List, Any


def scan_contracts() -> List[Dict[str, Any]]:
    """Scan all contract directories."""
    contracts = []

    contract_dirs = ["ann", "hybrid", "index", "schema"]

    for family in contract_dirs:
        family_path = Path(f"contracts/{family}")
        if not family_path.exists():
            continue

        for contract_file in family_path.glob("*.json"):
            try:
                data = json.loads(contract_file.read_text())
                contracts.append({
                    "contract_id": data.get("contract_id"),
                    "family": data.get("family", family.upper()),
                    "semantic_area": data.get("scope", {}).get("semantic_area", "unknown"),
                    "coverage_status": "unvalidated",
                    "validation_level": "static_only",
                    "validated_in_campaigns": [],
                    "result_file": None,
                    "case_evidence": [],
                    "report_ref": None,
                    "db_matrix_ref": "VALIDATION_MATRIX.json",
                    "framework_level_candidate": False,
                    "notes": "TODO: Update from campaign results"
                })
            except Exception as e:
                print(f"Warning: Could not parse {contract_file}: {e}")

    return contracts


def main():
    contracts = scan_contracts()

    # Build summary by family
    summary_by_family: Dict[str, Dict[str, int]] = {}
    for c in contracts:
        family = c["family"]
        if family not in summary_by_family:
            summary_by_family[family] = {"unvalidated": 0}
        summary_by_family[family]["unvalidated"] += 1

    # Build index
    index = {
        "last_updated": "2026-03-10",
        "total_contracts": len(contracts),
        "summary": {
            "contract_counts_by_family": {
                k: sum(v.values()) for k, v in summary_by_family.items()
            },
            "coverage_counts_by_family": summary_by_family
        },
        "contracts": contracts
    }

    # Write output
    output_path = Path("contracts/CONTRACT_COVERAGE_INDEX.json")
    output_path.write_text(json.dumps(index, indent=2))
    print(f"Generated: {output_path}")
    print(f"Total contracts: {len(contracts)}")

    return 0


if __name__ == "__main__":
    exit(main())
```

**Step 2: Run coverage index generation**

```bash
python scripts/generate_coverage_index.py
```

**Step 3: Create initial validation matrix (empty)**

```json
{
  "last_updated": "2026-03-10",
  "validations": []
}
```

**Step 4: Commit**

```bash
git add contracts/CONTRACT_COVERAGE_INDEX.json contracts/VALIDATION_MATRIX.json
git commit -m "feat(automation): add contract coverage index and validation matrix"
```

---

## Task 5: Update Coverage Index from R5B/R5D Results

**Files:**
- Modify: `contracts/CONTRACT_COVERAGE_INDEX.json`
- Modify: `contracts/VALIDATION_MATRIX.json`

**Step 1: Create result parser script**

```python
#!/usr/bin/env python3
"""Update contract coverage from existing result files."""

import json
from pathlib import Path
from datetime import datetime


def parse_result_file(result_path: Path) -> Dict[str, Any]:
    """Parse a result file and extract contract validations."""
    data = json.loads(result_path.read_text())

    return {
        "run_id": data.get("run_id"),
        "campaign": data.get("campaign"),
        "campaign_id": data.get("campaign_id"),
        "database_family": data.get("database", "").split()[0],
        "db_version": data.get("database", ""),
        "timestamp": data.get("timestamp"),
        "results": data.get("results", [])
    }


def main():
    # Parse R5B and R5D results
    result_files = [
        "results/r5b_lifecycle_20260310-124135.json",
        "results/r5d_p0_20260310-140345.json",
        "results/r5d_p05_20260310-141439.json"
    ]

    validations = []
    coverage_updates = {}

    for result_file in result_files:
        result_path = Path(result_file)
        if not result_path.exists():
            print(f"Warning: {result_file} not found, skipping")
            continue

        result = parse_result_file(result_path)

        for case_result in result["results"]:
            contract_id = case_result.get("contract_id")
            classification = case_result.get("oracle", {}).get("classification")
            case_id = case_result.get("case_id")

            # Add to validation matrix
            validations.append({
                "database_family": result["database_family"],
                "db_version": result["db_version"],
                "contract_id": contract_id,
                "status_scope": "case_level",
                "classification": classification,
                "case_id": case_id,
                "result_file": result_file,
                "report_ref": None,  # TODO: Map to actual report
                "campaign": result["campaign"],
                "timestamp": result["timestamp"]
            })

            # Track coverage updates
            if contract_id not in coverage_updates:
                coverage_updates[contract_id] = {
                    "validated_in_campaigns": set(),
                    "case_evidence": [],
                    "latest_status": classification
                }
            coverage_updates[contract_id]["validated_in_campaigns"].add(result["campaign"])
            coverage_updates[contract_id]["case_evidence"].append({
                "case_id": case_id,
                "classification": classification
            })

    # Write validation matrix
    matrix = {
        "last_updated": datetime.now().isoformat(),
        "validations": validations
    }
    Path("contracts/VALIDATION_MATRIX.json").write_text(json.dumps(matrix, indent=2))
    print(f"Updated VALIDATION_MATRIX.json with {len(validations)} validations")

    return 0


if __name__ == "__main__":
    exit(main())
```

**Step 2: Run result parser**

```bash
python scripts/update_coverage_from_results.py
```

**Step 3: Manually update coverage index based on validation matrix**

Edit `CONTRACT_COVERAGE_INDEX.json`:
- Update `coverage_status` based on validation matrix
- Update `validated_in_campaigns`
- Add `case_evidence`
- Update `summary` counts

**Step 4: Commit**

```bash
git add contracts/CONTRACT_COVERAGE_INDEX.json contracts/VALIDATION_MATRIX.json
git commit -m "feat(automation): update contract coverage from R5B/R5D results"
```

---

## Task 6: Create P3 Campaign Bootstrap Scaffold

**Files:**
- Create: `scripts/bootstrap_campaign.py`

**Step 1: Write bootstrap script**

```python
#!/usr/bin/env python3
"""Bootstrap a new campaign from YAML config.

Generates 8 skeleton artifacts for campaign development.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
import yaml


# Templates for each artifact
PLAN_TEMPLATE = """# {campaign_id} Campaign Plan

**Campaign ID**: {campaign_id}
**Target Database**: {target_db}
**Date**: {date}
**Status**: PLANNING

---

## Goal

{goal}

---

## Contract Families

{contract_families}

---

## Campaign Scope

**Mode**: {mode}
**Max Cases**: {max_cases}
**Runtime Budget**: {runtime_budget}

**Required Operations**:
{required_operations}

---

## TODO

- [ ] Define specific test cases
- [ ] Set up capability validation
- [ ] Define success criteria
"""

CONTRACT_TEMPLATE = """{{
  "contract_family": "{family}",
  "campaign": "{campaign_id}",
  "version": "1.0",
  "description": "Contract definitions for {campaign_id}",
  "contracts": [
    {{
      "contract_id": "TODO-001",
      "name": "TODO: Contract name",
      "statement": "TODO: Contract statement",
      "preconditions": [],
      "postconditions": [],
      "invariants": []
    }}
  ]
}}
"""

GENERATOR_TEMPLATE = '''"""Test case generator for {campaign_id}."""

from pathlib import Path
from typing import Dict, List, Any


class {campaign_class}Generator:
    """Generate test cases for {campaign_id}."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def generate(self) -> List[Dict[str, Any]]:
        """Generate test cases.

        TODO: Implement case generation logic
        """
        return []

    def save(self, cases: List[Dict[str, Any]], output_path: Path):
        """Save generated cases to file."""
        import json
        output_path.write_text(json.dumps(cases, indent=2))
'''

ORACLE_TEMPLATE = '''"""Oracle for {campaign_id}."""

from typing import Dict, Any, List


class {campaign_class}Oracle:
    """Oracle for evaluating {campaign_id} test results."""

    def evaluate(self, result: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate test result against contract.

        Args:
            result: Test execution result
            contract: Contract specification

        Returns:
            Oracle evaluation with classification and reasoning
        """
        # TODO: Implement oracle logic
        return {{
            "classification": "UNKNOWN",
            "reasoning": "TODO: Implement oracle evaluation"
        }}
'''

SMOKE_TEMPLATE = '''"""Smoke test runner for {campaign_id}."""

import argparse
import json
from pathlib import Path
from adapters.{adapter} import {adapter_class}


def main():
    parser = argparse.ArgumentParser(description="Run {campaign_id} smoke tests")
    parser.add_argument("--mode", default="REAL", choices=["MOCK", "REAL"])
    args = parser.parse_args()

    # TODO: Implement smoke test logic
    print("{campaign_id} smoke tests - TODO")

    return 0


if __name__ == "__main__":
    exit(main())
'''

REPORT_TEMPLATE = """# {campaign_id} Campaign Report

**Campaign ID**: {campaign_id}
**Date**: {date}
**Status**: TODO

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Cases | TODO |
| Passed | TODO |
| Failed | TODO |
| Observations | TODO |

---

## Case Results

TODO: Fill in case results

---

## Conclusions

TODO: Add campaign conclusions
"""

HANDOFF_TEMPLATE = """# {campaign_id} Campaign Handoff

**Campaign ID**: {campaign_id}
**Date**: {date}
**Status**: COMPLETE

---

## Summary

TODO: Campaign summary

---

## Completed Work

- [x] Campaign setup
- [x] Test execution
- [ ] TODO: Add completed items

---

## Artifacts

- Plan: `docs/plans/{campaign_id}_PLAN.md`
- Contracts: `contracts/{family}/{campaign_id}_contracts.json`
- Results: `results/{run_id}.json`

---

## Next Steps

1. TODO: Add next steps
2. TODO: Document follow-up items
"""


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load YAML config."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def generate_artifacts(config: Dict[str, Any], input_dir: Path) -> List[Dict[str, Any]]:
    """Generate all campaign artifacts."""
    artifacts = []
    campaign_id = config["campaign_id"]
    campaign_class = campaign_id.replace("-", "_")

    # 1. Plan skeleton
    plan_path = Path(f"docs/plans/{campaign_id}_PLAN.md")
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(PLAN_TEMPLATE.format(
        campaign_id=campaign_id,
        target_db=config["target_db"],
        date=datetime.now().strftime("%Y-%m-%d"),
        goal=config["goal"],
        contract_families=", ".join(config["contract_families"]),
        mode=config["mode"],
        max_cases=config["constraints"].get("max_cases", "TODO"),
        runtime_budget=config["constraints"].get("runtime_budget", "TODO"),
        required_objects="\n".join(f"- {op}" for op in config["constraints"].get("required_operations", []))
    ))
    artifacts.append({"type": "plan", "path": str(plan_path)})

    # 2. Contract spec skeleton (first family only)
    family = config["contract_families"][0].lower() if config["contract_families"] else "TODO"
    contract_path = Path(f"contracts/{family}/{campaign_id}_contracts.json")
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(CONTRACT_TEMPLATE.format(
        family=family.upper(),
        campaign_id=campaign_id
    ))
    artifacts.append({"type": "contract_spec", "path": str(contract_path)})

    # 3. Generator skeleton
    gen_path = Path(f"casegen/generators/{campaign_id}_generator.py")
    gen_path.parent.mkdir(parents=True, exist_ok=True)
    gen_path.write_text(GENERATOR_TEMPLATE.format(
        campaign_id=campaign_id,
        campaign_class=campaign_class
    ))
    artifacts.append({"type": "generator", "path": str(gen_path)})

    # 4. Oracle skeleton
    oracle_path = Path(f"pipeline/oracles/{campaign_id}_oracle.py")
    oracle_path.parent.mkdir(parents=True, exist_ok=True)
    oracle_path.write_text(ORACLE_TEMPLATE.format(
        campaign_id=campaign_id,
        campaign_class=campaign_class
    ))
    artifacts.append({"type": "oracle", "path": str(oracle_path)})

    # 5. Smoke runner skeleton
    adapter = config.get("adapter", "milvus_adapter")
    adapter_class = "".join(w.capitalize() for w in adapter.replace("_adapter", "").split("_")) + "Adapter"
    smoke_path = Path(f"scripts/run_{campaign_id}_smoke.py")
    smoke_path.write_text(SMOKE_TEMPLATE.format(
        campaign_id=campaign_id,
        adapter=adapter.replace("_adapter", ""),
        adapter_class=adapter_class
    ))
    artifacts.append({"type": "smoke_runner", "path": str(smoke_path)})

    # 6. Report template
    report_path = Path(f"docs/reports/{campaign_id}_REPORT_TEMPLATE.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(REPORT_TEMPLATE.format(
        campaign_id=campaign_id,
        date=datetime.now().strftime("%Y-%m-%d")
    ))
    artifacts.append({"type": "report_template", "path": str(report_path)})

    # 7. Handoff template
    handoff_path = Path(f"docs/handoffs/{campaign_id}_HANDOFF_TEMPLATE.md")
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(HANDOFF_TEMPLATE.format(
        campaign_id=campaign_id,
        family=family.upper(),
        date=datetime.now().strftime("%Y-%m-%d")
    ))
    artifacts.append({"type": "handoff_template", "path": str(handoff_path)})

    return artifacts


def main():
    parser = argparse.ArgumentParser(description="Bootstrap a new campaign")
    parser.add_argument("config", help="Path to campaign config YAML")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        return 1

    # Load config
    config = load_config(config_path)

    # Generate artifacts
    artifacts = generate_artifacts(config, config_path.parent)

    # Write manifest
    manifest = {
        "campaign_name": config["campaign_name"],
        "campaign_id": config["campaign_id"],
        "generated_at": datetime.now().isoformat(),
        "input_config": str(config_path),
        "artifacts": artifacts,
        "capability_registry_snapshot": config.get("input_registries", {}).get("capability_registry"),
        "contract_coverage_snapshot": config.get("input_registries", {}).get("contract_coverage")
    }

    manifest_path = config_path.parent / "bootstrap_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"Generated {len(artifacts)} artifacts:")
    for a in artifacts:
        print(f"  - {a['type']}: {a['path']}")
    print(f"Manifest: {manifest_path}")

    return 0


if __name__ == "__main__":
    exit(main())
```

**Step 2: Commit**

```bash
git add scripts/bootstrap_campaign.py
git commit -m "feat(automation): add campaign bootstrap script"
```

---

## Task 7: Create Campaign Config Example

**Files:**
- Create: `campaigns/example/config.yaml`

**Step 1: Create example campaign config**

```bash
mkdir -p campaigns/example
```

```yaml
# campaigns/example/config.yaml
campaign_name: "example_campaign"
campaign_id: "EXA-001"
target_db: "Milvus"
adapter: "milvus_adapter"
contract_families:
  - "ANN"
  - "INDEX"
goal: "Example campaign to demonstrate bootstrap scaffolding"
mode: "REAL"

constraints:
  max_cases: 10
  runtime_budget: "30m"
  required_operations:
    - "create_collection"
    - "insert"
    - "search"

preferences:
  priority_contracts:
    - "ANN-001"
  skip_contracts: []

input_registries:
  capability_registry: "capabilities/milvus_capabilities.json"
  contract_coverage: "contracts/CONTRACT_COVERAGE_INDEX.json"
  validation_matrix: "contracts/VALIDATION_MATRIX.json"
```

**Step 2: Test bootstrap script**

```bash
python scripts/bootstrap_campaign.py campaigns/example/config.yaml
```

**Step 3: Verify generated artifacts**

Check that 8 files were created:
- `docs/plans/EXA-001_PLAN.md`
- `contracts/ann/EXA-001_contracts.json`
- `casegen/generators/exa-001_generator.py`
- `pipeline/oracles/exa-001_oracle.py`
- `scripts/run_exa-001_smoke.py`
- `docs/reports/EXA-001_REPORT_TEMPLATE.md`
- `docs/handoffs/EXA-001_HANDOFF_TEMPLATE.md`
- `campaigns/example/bootstrap_manifest.json`

**Step 4: Commit**

```bash
git add campaigns/example/
git add docs/plans/EXA-001_PLAN.md
git add contracts/ann/EXA-001_contracts.json
git add casegen/generators/exa-001_generator.py
git add pipeline/oracles/exa-001_oracle.py
git add scripts/run_exa-001_smoke.py
git add docs/reports/EXA-001_REPORT_TEMPLATE.md
git add docs/handoffs/EXA-001_HANDOFF_TEMPLATE.md
git commit -m "feat(automation): add example campaign bootstrap test"
```

---

## Task 8: Create P4 Results Index Script

**Files:**
- Create: `scripts/index_results.py`

**Step 1: Write results index script**

```python
#!/usr/bin/env python3
"""Index all result files in results/ directory.

Generates RESULTS_INDEX.json (machine-readable) and RESULTS_INDEX.md (optional view).
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict


def parse_result_file(result_path: Path) -> Dict[str, Any]:
    """Parse a single result file."""
    try:
        data = json.loads(result_path.read_text())

        # Extract database family and version
        database_str = data.get("database", "")
        if " " in database_str:
            db_family, db_version = database_str.split(" ", 1)
        else:
            db_family = database_str
            db_version = "unknown"

        # Build classification summary
        results = data.get("results", [])
        classification_counts = defaultdict(int)
        for r in results:
            classification = r.get("oracle", {}).get("classification", "UNKNOWN")
            classification_counts[classification] += 1

        return {
            "run_id": data.get("run_id", result_path.stem),
            "campaign": data.get("campaign", "unknown"),
            "campaign_id": data.get("campaign_id"),
            "database_family": db_family,
            "db_version": db_version,
            "timestamp": data.get("timestamp"),
            "result_file": str(result_path),
            "mode": data.get("mode", "UNKNOWN"),
            "classification_summary": {
                "total": len(results),
                "by_classification": dict(classification_counts)
            },
            "linked_contracts": list(set(r.get("contract_id") for r in results)),
            "case_count": len(results),
            "report_ref": None,  # TODO: Auto-detect from docs/reports/
            "handoff_ref": None  # TODO: Auto-detect from docs/handoffs/
        }
    except Exception as e:
        print(f"Warning: Could not parse {result_path}: {e}")
        return None


def main():
    results_dir = Path("results")
    if not results_dir.exists():
        print(f"Error: results/ directory not found")
        return 1

    # Scan for JSON result files
    result_files = list(results_dir.glob("*.json"))
    # Exclude index files
    result_files = [f for f in result_files if "INDEX" not in f.name]

    runs = []
    summary_by_campaign = defaultdict(int)
    summary_by_db_version = defaultdict(int)

    for result_file in result_files:
        run_data = parse_result_file(result_file)
        if run_data:
            runs.append(run_data)
            summary_by_campaign[run_data["campaign"]] += 1
            db_key = f"{run_data['database_family']} {run_data['db_version']}"
            summary_by_db_version[db_key] += 1

    # Sort by timestamp
    runs.sort(key=lambda r: r.get("timestamp", ""))

    # Build index
    index = {
        "last_updated": datetime.now().isoformat(),
        "total_runs": len(runs),
        "summary": {
            "by_campaign": dict(summary_by_campaign),
            "by_database_version": dict(summary_by_db_version)
        },
        "runs": runs
    }

    # Write JSON index
    output_path = results_dir / "RESULTS_INDEX.json"
    output_path.write_text(json.dumps(index, indent=2))
    print(f"Generated: {output_path}")
    print(f"Total runs indexed: {len(runs)}")

    return 0


if __name__ == "__main__":
    exit(main())
```

**Step 2: Run index script**

```bash
python scripts/index_results.py
```

**Step 3: Commit**

```bash
git add scripts/index_results.py results/RESULTS_INDEX.json
git commit -m "feat(automation): add results index script"
```

---

## Task 9: Create P4 Diff Script

**Files:**
- Create: `scripts/diff_results.py`

**Step 1: Write diff script**

```python
#!/usr/bin/env python3
"""Compare two result runs and show differences."""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


def load_run(run_id: str, results_dir: Path) -> Dict[str, Any]:
    """Load a result file by run_id."""
    # Try to find the result file
    result_files = list(results_dir.glob(f"*{run_id}*.json"))
    result_files = [f for f in result_files if "INDEX" not in f.name]

    if not result_files:
        print(f"Error: Could not find result file for run_id '{run_id}'")
        sys.exit(1)

    if len(result_files) > 1:
        print(f"Warning: Multiple files found for '{run_id}', using first")

    result_path = result_files[0]
    return json.loads(result_path.read_text())


def get_cases_by_contract(run: Dict[str, Any]) -> Dict[str, List[Dict]]:
    """Group cases by contract_id."""
    by_contract = {}
    for result in run.get("results", []):
        contract_id = result.get("contract_id")
        if contract_id not in by_contract:
            by_contract[contract_id] = []
        by_contract[contract_id].append(result)
    return by_contract


def main():
    parser = argparse.ArgumentParser(description="Diff two result runs")
    parser.add_argument("run1", help="First run_id (e.g., r5d-p0-20260310-140340)")
    parser.add_argument("run2", help="Second run_id (e.g., r5d-p05-20260310-141433)")
    args = parser.parse_args()

    results_dir = Path("results")

    # Load runs
    run1 = load_run(args.run1, results_dir)
    run2 = load_run(args.run2, results_dir)

    # Group cases by contract
    cases1 = get_cases_by_contract(run1)
    cases2 = get_cases_by_contract(run2)

    # Compute diff
    delta = {
        "cases_added": [],
        "cases_removed": [],
        "classification_changes": [],
        "new_observations": [],
        "bug_candidates": {"introduced": [], "resolved": []},
        "contract_status_changes": [],
        "summary_delta": {}
    }

    # Find added/removed cases
    all_case_ids = set()
    cases_by_id1 = {}
    cases_by_id2 = {}

    for result in run1.get("results", []):
        case_id = result.get("case_id")
        all_case_ids.add(case_id)
        cases_by_id1[case_id] = result

    for result in run2.get("results", []):
        case_id = result.get("case_id")
        all_case_ids.add(case_id)
        cases_by_id2[case_id] = result

    # Cases added in run2
    for case_id, result in cases_by_id2.items():
        if case_id not in cases_by_id1:
            delta["cases_added"].append({
                "case_id": case_id,
                "contract_id": result.get("contract_id")
            })

    # Cases removed in run2
    for case_id, result in cases_by_id1.items():
        if case_id not in cases_by_id2:
            delta["cases_removed"].append({
                "case_id": case_id,
                "contract_id": result.get("contract_id")
            })

    # Classification changes
    for case_id in all_case_ids:
        if case_id in cases_by_id1 and case_id in cases_by_id2:
            class1 = cases_by_id1[case_id].get("oracle", {}).get("classification")
            class2 = cases_by_id2[case_id].get("oracle", {}).get("classification")
            if class1 != class2:
                delta["classification_changes"].append({
                    "case_id": case_id,
                    "contract_id": cases_by_id1[case_id].get("contract_id"),
                    "from": class1,
                    "to": class2
                })

                # Track bug candidates
                if class2 == "BUG_CANDIDATE":
                    delta["bug_candidates"]["introduced"].append({"case_id": case_id})
                if class1 == "BUG_CANDIDATE" and class2 != "BUG_CANDIDATE":
                    delta["bug_candidates"]["resolved"].append({"case_id": case_id})

    # Summary delta
    summary1 = run1.get("summary", {})
    summary2 = run2.get("summary", {})
    by_class1 = summary1.get("by_classification", {})
    by_class2 = summary2.get("by_classification", {})

    for cls in set(list(by_class1.keys()) + list(by_class2.keys())):
        from_count = by_class1.get(cls, 0)
        to_count = by_class2.get(cls, 0)
        if from_count != to_count:
            delta["summary_delta"][f"by_classification.{cls}"] = {
                "from": from_count,
                "to": to_count
            }

    delta["summary_delta"]["total"] = {
        "from": summary1.get("total", 0),
        "to": summary2.get("total", 0)
    }

    # Build diff output
    diff_output = {
        "diff_id": f"{args.run1}-vs-{args.run2}",
        "comparison_scope": "run_to_run",
        "run1": args.run1,
        "run2": args.run2,
        "timestamp": datetime.now().isoformat(),
        "delta": delta
    }

    # Write output
    output_path = results_dir / f"diff_{args.run1}_vs_{args.run2}.json"
    output_path.write_text(json.dumps(diff_output, indent=2))
    print(f"Generated: {output_path}")

    # Print summary
    print(f"\nDiff: {args.run1} → {args.run2}")
    print(f"  Cases added: {len(delta['cases_added'])}")
    print(f"  Cases removed: {len(delta['cases_removed'])}")
    print(f"  Classification changes: {len(delta['classification_changes'])}")
    print(f"  Bug candidates introduced: {len(delta['bug_candidates']['introduced'])}")
    print(f"  Bug candidates resolved: {len(delta['bug_candidates']['resolved'])}")

    return 0


if __name__ == "__main__":
    exit(main())
```

**Step 2: Test diff script**

```bash
python scripts/diff_results.py r5d-p0-20260310-140340 r5d-p05-20260310-141433
```

**Step 3: Commit**

```bash
git add scripts/diff_results.py results/diff_*.json
git commit -m "feat(automation): add results diff script"
```

---

## Task 10: Create Documentation README

**Files:**
- Create: `docs/AUTOMATION_README.md`

**Step 1: Write automation README**

```markdown
# Automation Acceleration

Campaign bootstrapping infrastructure to reduce startup cost.

## Quick Start

### Bootstrap a New Campaign

1. Create campaign config:
```yaml
# campaigns/my_campaign/config.yaml
campaign_name: "my_campaign"
campaign_id: "R7A-001"
target_db: "Milvus"
adapter: "milvus_adapter"
contract_families: ["ANN"]
goal: "Test ANN properties"
mode: "REAL"
```

2. Run bootstrap:
```bash
python scripts/bootstrap_campaign.py campaigns/my_campaign/config.yaml
```

3. Implement the generated skeletons (TODOs marked in files)

### Index Results

```bash
python scripts/index_results.py
```

### Compare Runs

```bash
python scripts/diff_results.py r5d-p0-20260310-140340 r5d-p05-20260310-141433
```

### Update Capability Registries

```bash
python scripts/bootstrap_capability_registry.py --adapter milvus
```

## Components

| Component | Script | Purpose |
|-----------|--------|---------|
| P1 | `bootstrap_capability_registry.py` | Scan adapter for operations |
| P2 | (manual) | Update contract coverage from results |
| P3 | `bootstrap_campaign.py` | Generate campaign skeletons |
| P4 | `index_results.py` | Index all result files |
| P4 | `diff_results.py` | Compare two runs |

## File Structure

```
capabilities/              # P1: Capability registries
├── *_capabilities.json
contracts/
├── CONTRACT_COVERAGE_INDEX.json  # P2: Coverage status
├── VALIDATION_MATRIX.json        # P2: Cross-DB matrix
campaigns/                 # P3: Campaign configs
└── {name}/
    ├── config.yaml
    └── bootstrap_manifest.json
results/
├── RESULTS_INDEX.json     # P4: Results index
└── diff_*.json            # P4: Diff outputs
scripts/
├── bootstrap_capability_registry.py
├── bootstrap_campaign.py
├── index_results.py
└── diff_results.py
```

## Design Document

See `docs/plans/2026-03-10-AUTOMATION_ACCELERATION_MVP.md` for full design.
```

**Step 2: Commit**

```bash
git add docs/AUTOMATION_README.md
git commit -m "docs(automation): add automation quick start guide"
```

---

## Summary

**Total Tasks**: 10
**Estimated Time**: 2-3 hours
**Deliverables**:
- P1: 4 capability registries + bootstrap script
- P2: Contract coverage index + validation matrix
- P3: Campaign bootstrap script (8 artifacts)
- P4: Results index + diff scripts
- Documentation

**Success Criteria**:
- New campaign can be bootstrapped with single command
- Results are indexable and comparable
- Campaign startup time reduced by 50-70%

---

**Plan Version**: 1.0
**Date**: 2026-03-10
**Status**: READY FOR EXECUTION
