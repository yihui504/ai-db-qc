# Automation Acceleration MVP - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build campaign bootstrapping infrastructure to reduce new campaign startup cost by 50-70%.

**Architecture:** Four-component system:
- P1: Declarative capability registry (static scan + manual tuning)
- P2: Contract coverage index (immutable contracts + dynamic status, auto-generated)
- P3: Campaign bootstrap scaffold (YAML config → 8 artifacts)
- P4: Results index/diff (manual, explicit comparison)

**Tech Stack:** Python 3.10+, JSON schemas, argparse, pathlib

**Commit Strategy:** Per-component commits (P1, P2, P3, P4), not per-task

---

# Phase P1: Capability Audit Registry

## P1.1: Create Directory Structure

**Files:**
- Create: `capabilities/README.md`
- Create: `capabilities/.gitkeep`

**Step 1: Create capabilities directory**

```bash
mkdir -p capabilities
touch capabilities/.gitkeep
```

**Step 2: Create README**

```markdown
# Capability Registry

Declarative capability declarations for each database adapter.

## Files

- `milvus_capabilities.json` - Milvus adapter capabilities
- `qdrant_capabilities.json` - Qdrant adapter capabilities
- `seekdb_capabilities.json` - SeekDB adapter capabilities
- `mock_capabilities.json` - Mock adapter capabilities

## Schema

See `docs/plans/2026-03-10-AUTOMATION_ACCELERATION_MVP.md` for full schema.

## Updating

Run `python scripts/bootstrap_capability_registry.py --adapter <name>` to regenerate from adapter code.
Manual review required for: support_status, confidence, known_constraints, notes.
```

---

## P1.2: Implement Capability Scanner with Dispatch Mapping

**Files:**
- Create: `scripts/bootstrap_capability_registry.py`

**Key Design Changes:**
1. **Priority**: Scan adapter `execute()` method dispatch mapping first
2. **Fallback**: Scan for `_operation()` helper methods
3. **Distinguish**: Core operations vs helper methods
4. **Filter**: Exclude pure helpers (_connect, _format_output, etc.)

**Step 1: Write improved scanner**

```python
#!/usr/bin/env python3
"""Bootstrap capability registry from adapter code.

Priority: Scan execute() dispatch mapping first
Fallback: Scan _operation() methods
Filter: Exclude pure helper methods
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Set


# Known helper methods to exclude (not operations)
HELPER_METHODS = {
    "_connect", "_format_output", "_parse_response", "_validate_params",
    "_build_schema", "_get_collection", "health_check", "close",
    "get_runtime_snapshot", "__init__"
}


class CapabilityScanner:
    """Scan adapter code to extract operations."""

    def __init__(self, adapter_path: Path):
        self.adapter_path = adapter_path

    def scan_execute_dispatch(self, content: str) -> Set[str]:
        """Extract operations from execute() method's if/elif chain.

        Priority method: Most adapters explicitly map operation names.
        """
        operations = set()

        # Find execute method body
        execute_match = re.search(
            r'def execute\(self[^)]*\):(.*?)(?=\n    def |\nclass |\Z)',
            content,
            re.DOTALL
        )

        if execute_match:
            execute_body = execute_match.group(1)
            # Find operation == "xxx" patterns
            op_patterns = [
                r'operation\s*==\s*["\'](\w+)["\']',
                r'elif\s+operation\s*==\s*["\'](\w+)["\']:',
                r'if\s+operation\s*==\s*["\'](\w+)["\']:',
            ]
            for pattern in op_patterns:
                matches = re.findall(pattern, execute_body)
                operations.update(matches)

        return operations

    def scan_private_methods(self, content: str) -> Set[str]:
        """Fallback: Extract from _operation() methods.

        Filters out known helper methods.
        """
        operations = set()

        # Find all _method definitions
        for match in re.finditer(r'def (_\w+)\(', content):
            method_name = match.group(1)
            if method_name not in HELPER_METHODS:
                operations.add(method_name.lstrip("_"))

        return operations

    def scan(self) -> List[Dict[str, Any]]:
        """Scan adapter file for operations.

        Returns:
            List of operation dicts
        """
        content = self.adapter_path.read_text()

        # Priority 1: Scan execute() dispatch
        operations = self.scan_execute_dispatch(content)

        # Priority 2: Fallback to _operation methods
        if not operations:
            operations = self.scan_private_methods(content)

        # Build operation list
        result = []
        for op_name in sorted(operations):
            result.append({
                "operation": op_name,
                "support_status": "unknown",
                "support_level": "static_only",
                "confidence": "low",
                "implementation_path": f"{self.adapter_path.stem}Adapter._{op_name if not op_name.startswith('_') else op_name}",
                "verification_path": None,
                "known_constraints": [],
                "evidence_source": "static_scan",
                "validated_in_campaigns": [],
                "notes": "TODO: Manual review required"
            })

        return result


def main():
    parser = argparse.ArgumentParser(description="Bootstrap capability registry")
    parser.add_argument("--adapter", required=True,
                        help="Adapter name (milvus, qdrant, seekdb, mock)")
    parser.add_argument("--output", default="capabilities", help="Output directory")
    args = parser.parse_args()

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

    # Extract SDK version from imports
    content = adapter_path.read_text()
    sdk_version = "TODO"
    version_match = re.search(r'pymilvus\s*==\s*([\d.]+)', content)
    if version_match:
        sdk_version = f"pymilvus v{version_match.group(1)}"

    # Build registry
    registry = {
        "adapter_name": f"{args.adapter}_adapter",
        "db_family": args.adapter.capitalize(),
        "sdk_version": sdk_version,
        "validated_db_version": "TODO",
        "last_updated": "2026-03-10",
        "operations": operations
    }

    # Write output
    output_path = Path(args.output) / f"{args.adapter}_capabilities.json"
    output_path.write_text(json.dumps(registry, indent=2))
    print(f"Generated: {output_path}")
    print(f"Found {len(operations)} operations")
    print("Please review and update:")
    print("  - sdk_version")
    print("  - support_status (supported/unsupported/partially_supported)")
    print("  - confidence (high/medium/low)")
    print("  - known_constraints")
    print("  - validated_in_campaigns")
    print("  - notes")

    return 0


if __name__ == "__main__":
    exit(main())
```

---

## P1.3: Generate and Review Capability Registries

**Step 1: Generate all 4 registries**

```bash
python scripts/bootstrap_capability_registry.py --adapter milvus
python scripts/bootstrap_capability_registry.py --adapter qdrant
python scripts/bootstrap_capability_registry.py --adapter seekdb
python scripts/bootstrap_capability_registry.py --adapter mock
```

**Step 2: Manual review required for each file**

Edit each `capabilities/*_capabilities.json`:
- `sdk_version`: Verify actual version
- `validated_db_version`: Add tested DB version
- `support_status`: Change unknown → supported/unsupported/partially_supported
- `confidence`: Set high/medium/low based on evidence
- `known_constraints`: Add known limitations
- `validated_in_campaigns`: Add campaign names if validated
- `notes`: Add context

---

## P1.4: Commit P1 Component

```bash
git add capabilities/ scripts/bootstrap_capability_registry.py
git commit -m "feat(automation): P1 capability registry with dispatch-first scanning

- Add bootstrap_capability_registry.py with execute() dispatch priority
- Generate initial capability registries for all adapters
- Filter out helper methods, focus on core operations
- Manual review required for support_status, confidence, constraints

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

# Phase P2: Contract Coverage Index (Auto-Generated)

## P2.1: Create Contract Scanner

**Files:**
- Create: `scripts/generate_contract_coverage.py`

**Key Design Changes:**
1. **VALIDATION_MATRIX.json** is source of truth for validation status
2. **CONTRACT_COVERAGE_INDEX.json** is auto-generated from:
   - Contract definitions (static metadata)
   - Validation matrix (dynamic status)
3. **Manual input**: Only stable_metadata (framework_level_candidate, notes)

**Step 1: Write coverage generator**

```python
#!/usr/bin/env python3
"""Generate contract coverage index from contracts + validation matrix.

Source of truth:
- Contract definitions: stable metadata (contract_id, family, statement)
- VALIDATION_MATRIX.json: dynamic validation status

Output:
- CONTRACT_COVERAGE_INDEX.json: Auto-generated merge

Manual input only:
- framework_level_candidate (in contract files)
- notes (in contract files)
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
from datetime import datetime


def load_contract_definitions() -> Dict[str, Dict[str, Any]]:
    """Load all contract definitions.

    Returns:
        Dict mapping contract_id to contract definition
    """
    contracts = {}
    contract_dirs = ["ann", "hybrid", "index", "schema"]

    for family in contract_dirs:
        family_path = Path(f"contracts/{family}")
        if not family_path.exists():
            continue

        for contract_file in family_path.glob("*.json"):
            try:
                data = json.loads(contract_file.read_text())
                contract_id = data.get("contract_id")
                if contract_id:
                    contracts[contract_id] = {
                        "contract_id": contract_id,
                        "family": data.get("family", family.upper()),
                        "statement": data.get("statement", ""),
                        "semantic_area": data.get("scope", {}).get("semantic_area", "unknown"),
                        "stable_metadata": {
                            "maturity": data.get("metadata", {}).get("confidence", "unknown"),
                            "intended_scope": data.get("scope", {}).get("databases", ["all"]),
                            "framework_level_candidate": False  # Default, can be set in contract file
                        }
                    }
            except Exception as e:
                print(f"Warning: Could not parse {contract_file}: {e}")

    return contracts


def load_validation_matrix() -> List[Dict[str, Any]]:
    """Load validation matrix (source of truth for validation status)."""
    matrix_path = Path("contracts/VALIDATION_MATRIX.json")
    if not matrix_path.exists():
        return []

    data = json.loads(matrix_path.read_text())
    return data.get("validations", [])


def compute_coverage_status(
    validations: List[Dict[str, Any]]
) -> tuple[str, str]:
    """Compute coverage_status and validation_level from validations.

    Args:
        validations: List of validation entries for a contract

    Returns:
        (coverage_status, validation_level)
    """
    if not validations:
        return "unvalidated", "static_only"

    # Check classifications
    classifications = [v.get("classification") for v in validations]

    # Strong: All PASS
    if all(c == "PASS" for c in classifications):
        return "strongly_validated", "campaign_validated"

    # Inconclusive: Has EXPERIMENT_DESIGN_ISSUE
    if "EXPERIMENT_DESIGN_ISSUE" in classifications:
        return "inconclusive", "campaign_validated"

    # Observational: Has OBSERVATION but no bugs
    if any(c in ["OBSERVATION", "EXPECTED_FAILURE"] for c in classifications):
        return "observational_only", "campaign_validated"

    # Partial: Mix of PASS/OBSERVATION
    if "PASS" in classifications:
        return "partially_validated", "campaign_validated"

    # Default
    return "unvalidated", "static_only"


def generate_coverage_index():
    """Generate CONTRACT_COVERAGE_INDEX.json from contracts + validation matrix."""
    # Load sources
    contracts = load_contract_definitions()
    validations = load_validation_matrix()

    # Group validations by contract
    validations_by_contract: Dict[str, List[Dict]] = defaultdict(list)
    campaigns_by_contract: Dict[str, set] = defaultdict(set)
    case_evidence_by_contract: Dict[str, List[Dict]] = defaultdict(list)

    for v in validations:
        contract_id = v.get("contract_id")
        validations_by_contract[contract_id].append(v)
        campaigns_by_contract[contract_id].add(v.get("campaign"))
        case_evidence_by_contract[contract_id].append({
            "case_id": v.get("case_id"),
            "classification": v.get("classification")
        })

    # Build coverage index
    coverage_contracts = []
    summary_by_family: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for contract_id, contract_def in contracts.items():
        validations = validations_by_contract.get(contract_id, [])
        coverage_status, validation_level = compute_coverage_status(validations)

        entry = {
            "contract_id": contract_id,
            "family": contract_def["family"],
            "semantic_area": contract_def["semantic_area"],
            "coverage_status": coverage_status,
            "validation_level": validation_level,
            "validated_in_campaigns": sorted(campaigns_by_contract.get(contract_id, set())),
            "case_evidence": case_evidence_by_contract.get(contract_id, []),
            "report_ref": None,  # TODO: Auto-detect from docs/reports/
            "db_matrix_ref": "VALIDATION_MATRIX.json",
            "framework_level_candidate": contract_def["stable_metadata"].get("framework_level_candidate", False),
            "notes": "Auto-generated from validation matrix"
        }
        coverage_contracts.append(entry)

        # Update summary
        family = entry["family"]
        summary_by_family[family][coverage_status] += 1

    # Build summary
    contract_counts_by_family = {
        k: sum(v.values()) for k, v in summary_by_family.items()
    }

    # Write output
    index = {
        "last_updated": datetime.now().isoformat(),
        "total_contracts": len(coverage_contracts),
        "summary": {
            "contract_counts_by_family": contract_counts_by_family,
            "coverage_counts_by_family": {k: dict(v) for k, v in summary_by_family.items()}
        },
        "contracts": coverage_contracts,
        "_generated_from": ["contract_definitions", "VALIDATION_MATRIX.json"]
    }

    output_path = Path("contracts/CONTRACT_COVERAGE_INDEX.json")
    output_path.write_text(json.dumps(index, indent=2))
    print(f"Generated: {output_path}")
    print(f"Total contracts: {len(coverage_contracts)}")

    return 0


if __name__ == "__main__":
    exit(generate_coverage_index())
```

---

## P2.2: Create Validation Matrix Populator

**Files:**
- Create: `scripts/populate_validation_matrix.py`

**Step 1: Write matrix populator**

```python
#!/usr/bin/env python3
"""Populate VALIDATION_MATRIX.json from existing result files.

VALIDATION_MATRIX.json is the source of truth for:
- What contract was tested on which database/version
- What classification was achieved
- Link to result file and case
"""

import json
from pathlib import Path
from datetime import datetime


def main():
    # Result files to process
    result_files = [
        "results/r5b_lifecycle_20260310-124135.json",
        "results/r5d_p0_20260310-140345.json",
        "results/r5d_p05_20260310-141439.json"
    ]

    validations = []

    for result_file in result_files:
        result_path = Path(result_file)
        if not result_path.exists():
            print(f"Warning: {result_file} not found, skipping")
            continue

        data = json.loads(result_path.read_text())

        # Extract database info
        database_str = data.get("database", "")
        if " " in database_str:
            db_family, db_version = database_str.split(" ", 1)
        else:
            db_family = database_str
            db_version = "unknown"

        # Process each result
        for case_result in data.get("results", []):
            validations.append({
                "database_family": db_family,
                "db_version": db_version,
                "contract_id": case_result.get("contract_id"),
                "status_scope": "case_level",
                "classification": case_result.get("oracle", {}).get("classification"),
                "case_id": case_result.get("case_id"),
                "result_file": result_file,
                "report_ref": None,  # TODO: Auto-detect
                "campaign": data.get("campaign"),
                "timestamp": data.get("timestamp")
            })

    # Write validation matrix
    matrix = {
        "last_updated": datetime.now().isoformat(),
        "validations": validations
    }

    output_path = Path("contracts/VALIDATION_MATRIX.json")
    output_path.write_text(json.dumps(matrix, indent=2))
    print(f"Generated: {output_path}")
    print(f"Total validations: {len(validations)}")

    return 0


if __name__ == "__main__":
    exit(main())
```

---

## P2.3: Initialize and Run P2

**Step 1: Create empty validation matrix**

```bash
echo '{"last_updated": "2026-03-10", "validations": []}' > contracts/VALIDATION_MATRIX.json
```

**Step 2: Populate validation matrix from results**

```bash
python scripts/populate_validation_matrix.py
```

**Step 3: Generate contract coverage index**

```bash
python scripts/generate_contract_coverage.py
```

---

## P2.4: Commit P2 Component

```bash
git add contracts/CONTRACT_COVERAGE_INDEX.json contracts/VALIDATION_MATRIX.json
git add scripts/generate_contract_coverage.py scripts/populate_validation_matrix.py
git commit -m "feat(automation): P2 contract coverage with auto-generation

- VALIDATION_MATRIX.json as source of truth for validation status
- CONTRACT_COVERAGE_INDEX.json auto-generated from contracts + matrix
- Manual input only for stable_metadata (framework_level_candidate, notes)
- Coverage status computed from validation matrix classifications

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

# Phase P3: Campaign Bootstrap Scaffold

## P3.1: Create Bootstrap Script with Fixes

**Files:**
- Create: `scripts/bootstrap_campaign.py`

**Key Fixes:**
1. Fix `required_objects` → `required_operations` in PLAN_TEMPLATE
2. Use python-safe slug for file names (convert hyphens to underscores)
3. MVP: Support one primary contract_family only

**Step 1: Write bootstrap script**

```python
#!/usr/bin/env python3
"""Bootstrap a new campaign from YAML config.

Generates 8 skeleton artifacts for campaign development.

MVP: Supports one primary contract_family only.
File naming: Python-safe slugs (underscores, no hyphens).
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import yaml


def to_python_slug(name: str) -> str:
    """Convert campaign_id to python-safe slug.

    Example: R6A-001 → r6a_001
    """
    return name.lower().replace("-", "_")


# Templates
PLAN_TEMPLATE = """# {campaign_id} Campaign Plan

**Campaign ID**: {campaign_id}
**Campaign Name**: {campaign_name}
**Target Database**: {target_db}
**Date**: {date}
**Status**: PLANNING

---

## Goal

{goal}

---

## Contract Family

**Primary Family**: {contract_family}

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
      "contract_id": "{family}-001",
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


class {class_name}Generator:
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

from typing import Dict, Any


class {class_name}Oracle:
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
from pathlib import Path
from adapters.{adapter_module} import {adapter_class}


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
- Contracts: `contracts/{family}/{campaign_slug}_contracts.json`
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
    campaign_slug = to_python_slug(campaign_id)
    class_name = "".join(w.capitalize() for w in campaign_slug.split("_"))

    # MVP: Support one primary family only
    families = config.get("contract_families", [])
    if not families:
        primary_family = "TODO"
    elif len(families) > 1:
        print(f"Warning: MVP supports one family only. Using: {families[0]}")
        primary_family = families[0].upper()
    else:
        primary_family = families[0].upper()

    family_dir = primary_family.lower()

    # 1. Plan skeleton
    plan_path = Path(f"docs/plans/{campaign_id}_PLAN.md")
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(PLAN_TEMPLATE.format(
        campaign_id=campaign_id,
        campaign_name=config.get("campaign_name", campaign_id),
        target_db=config["target_db"],
        date=datetime.now().strftime("%Y-%m-%d"),
        goal=config["goal"],
        contract_family=primary_family,
        mode=config["mode"],
        max_cases=config["constraints"].get("max_cases", "TODO"),
        runtime_budget=config["constraints"].get("runtime_budget", "TODO"),
        required_operations="\n".join(
            f"- {op}" for op in config["constraints"].get("required_operations", [])
        )
    ))
    artifacts.append({"type": "plan", "path": str(plan_path)})

    # 2. Contract spec skeleton
    contract_path = Path(f"contracts/{family_dir}/{campaign_slug}_contracts.json")
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(CONTRACT_TEMPLATE.format(
        family=primary_family,
        campaign_id=campaign_id
    ))
    artifacts.append({"type": "contract_spec", "path": str(contract_path)})

    # 3. Generator skeleton (python-safe filename)
    gen_path = Path(f"casegen/generators/{campaign_slug}_generator.py")
    gen_path.parent.mkdir(parents=True, exist_ok=True)
    gen_path.write_text(GENERATOR_TEMPLATE.format(
        campaign_id=campaign_id,
        class_name=class_name
    ))
    artifacts.append({"type": "generator", "path": str(gen_path)})

    # 4. Oracle skeleton (python-safe filename)
    oracle_path = Path(f"pipeline/oracles/{campaign_slug}_oracle.py")
    oracle_path.parent.mkdir(parents=True, exist_ok=True)
    oracle_path.write_text(ORACLE_TEMPLATE.format(
        campaign_id=campaign_id,
        class_name=class_name
    ))
    artifacts.append({"type": "oracle", "path": str(oracle_path)})

    # 5. Smoke runner skeleton (python-safe filename)
    adapter = config.get("adapter", "milvus_adapter")
    adapter_module = adapter.replace("_adapter", "")
    adapter_class = "".join(w.capitalize() for w in adapter_module.split("_")) + "Adapter"
    smoke_path = Path(f"scripts/run_{campaign_slug}_smoke.py")
    smoke_path.write_text(SMOKE_TEMPLATE.format(
        campaign_id=campaign_id,
        adapter_module=adapter_module,
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
        family=primary_family,
        campaign_slug=campaign_slug,
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

    config = load_config(config_path)

    # Generate artifacts
    artifacts = generate_artifacts(config, config_path.parent)

    # Write manifest
    manifest = {
        "campaign_name": config.get("campaign_name", config["campaign_id"]),
        "campaign_id": config["campaign_id"],
        "generated_at": datetime.now().isoformat(),
        "input_config": str(config_path),
        "artifacts": artifacts,
        "mvp_note": "Single contract family supported. Multi-family coming later.",
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

---

## P3.2: Create Example Campaign Config

**Files:**
- Create: `campaigns/example/config.yaml`

**Step 1: Create directory and config**

```bash
mkdir -p campaigns/example
```

```yaml
# campaigns/example/config.yaml
campaign_name: "example_campaign"
campaign_id: "EXA-001"
target_db: "Milvus"
adapter: "milvus_adapter"
# MVP: One family only
contract_families:
  - "ANN"
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

---

## P3.3: Test Bootstrap

**Step 1: Run bootstrap**

```bash
python scripts/bootstrap_campaign.py campaigns/example/config.yaml
```

**Step 2: Verify generated artifacts**

Check 8 files created:
- `docs/plans/EXA-001_PLAN.md`
- `contracts/ann/exa_001_contracts.json` (python-safe slug)
- `casegen/generators/exa_001_generator.py` (python-safe slug)
- `pipeline/oracles/exa_001_oracle.py` (python-safe slug)
- `scripts/run_exa_001_smoke.py` (python-safe slug)
- `docs/reports/EXA-001_REPORT_TEMPLATE.md`
- `docs/handoffs/EXA-001_HANDOFF_TEMPLATE.md`
- `campaigns/example/bootstrap_manifest.json`

---

## P3.4: Commit P3 Component

```bash
git add scripts/bootstrap_campaign.py campaigns/example/
git add docs/plans/EXA-001_PLAN.md
git add contracts/ann/exa_001_contracts.json
git add casegen/generators/exa_001_generator.py
git add pipeline/oracles/exa_001_oracle.py
git add scripts/run_exa_001_smoke.py
git add docs/reports/EXA-001_REPORT_TEMPLATE.md
git add docs/handoffs/EXA-001_HANDOFF_TEMPLATE.md
git commit -m "feat(automation): P3 campaign bootstrap with MVP single-family support

- Generate 8 skeleton artifacts from YAML config
- Fixed: required_operations (not required_objects) in plan template
- Fixed: Python-safe slugs for file names (underscores, not hyphens)
- MVP: Single contract_family support (multi-family future work)
- Added bootstrap_manifest.json for tracking

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

# Phase P4: Results Index and Diff

## P4.1: Create Results Index Script

**Files:**
- Create: `scripts/index_results.py`

**Step 1: Write index script**

```python
#!/usr/bin/env python3
"""Index all result files in results/ directory.

Generates RESULTS_INDEX.json (machine-readable).
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from collections import defaultdict


def parse_result_file(result_path: Path) -> Dict[str, Any] | None:
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
            "report_ref": None,  # TODO: Auto-detect
            "handoff_ref": None
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
    result_files = [f for f in result_files if "INDEX" not in f.name and "diff_" not in f.name]

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

    # Write output
    output_path = results_dir / "RESULTS_INDEX.json"
    output_path.write_text(json.dumps(index, indent=2))
    print(f"Generated: {output_path}")
    print(f"Total runs indexed: {len(runs)}")

    return 0


if __name__ == "__main__":
    exit(main())
```

---

## P4.2: Create Diff Script (Index-Based)

**Files:**
- Create: `scripts/diff_results.py`

**Key Fix:**
- Read RESULTS_INDEX.json first
- Use run_id to locate result_file
- Then load full result data

**Step 1: Write diff script**

```python
#!/usr/bin/env python3
"""Compare two result runs and show differences.

Reads RESULTS_INDEX.json to locate result files by run_id.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def load_results_index() -> Dict[str, Any]:
    """Load RESULTS_INDEX.json."""
    index_path = Path("results/RESULTS_INDEX.json")
    if not index_path.exists():
        print(f"Error: RESULTS_INDEX.json not found. Run index_results.py first.")
        sys.exit(1)
    return json.loads(index_path.read_text())


def find_result_file(run_id: str, index: Dict[str, Any]) -> str:
    """Find result file path by run_id from index."""
    for run in index.get("runs", []):
        if run.get("run_id") == run_id:
            return run.get("result_file")

    print(f"Error: run_id '{run_id}' not found in RESULTS_INDEX.json")
    print(f"Available run_ids: {[r['run_id'] for r in index.get('runs', [])]}")
    sys.exit(1)


def load_run(run_id: str, result_file: str) -> Dict[str, Any]:
    """Load a result file."""
    result_path = Path(result_file)
    if not result_path.exists():
        print(f"Error: Result file not found: {result_file}")
        sys.exit(1)
    return json.loads(result_path.read_text())


def main():
    parser = argparse.ArgumentParser(description="Diff two result runs")
    parser.add_argument("run1", help="First run_id (e.g., r5d-p0-20260310-140340)")
    parser.add_argument("run2", help="Second run_id (e.g., r5d-p05-20260310-141433)")
    args = parser.parse_args()

    # Load index
    index = load_results_index()

    # Find result files
    result_file1 = find_result_file(args.run1, index)
    result_file2 = find_result_file(args.run2, index)

    print(f"Loading {args.run1} from {result_file1}")
    print(f"Loading {args.run2} from {result_file2}")

    # Load runs
    run1 = load_run(args.run1, result_file1)
    run2 = load_run(args.run2, result_file2)

    # Group cases
    cases_by_id1 = {r.get("case_id"): r for r in run1.get("results", [])}
    cases_by_id2 = {r.get("case_id"): r for r in run2.get("results", [])}

    all_case_ids = set(cases_by_id1.keys()) | set(cases_by_id2.keys())

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

    # Cases added/removed
    for case_id in all_case_ids:
        if case_id in cases_by_id2 and case_id not in cases_by_id1:
            delta["cases_added"].append({
                "case_id": case_id,
                "contract_id": cases_by_id2[case_id].get("contract_id")
            })
        elif case_id in cases_by_id1 and case_id not in cases_by_id2:
            delta["cases_removed"].append({
                "case_id": case_id,
                "contract_id": cases_by_id1[case_id].get("contract_id")
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

    # Build output
    diff_output = {
        "diff_id": f"{args.run1}-vs-{args.run2}",
        "comparison_scope": "run_to_run",
        "run1": args.run1,
        "run2": args.run2,
        "timestamp": datetime.now().isoformat(),
        "delta": delta
    }

    # Write output
    results_dir = Path("results")
    output_path = results_dir / f"diff_{args.run1}_vs_{args.run2}.json"
    output_path.write_text(json.dumps(diff_output, indent=2))
    print(f"\nGenerated: {output_path}")

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

---

## P4.3: Initialize Index and Test Diff

**Step 1: Generate initial index**

```bash
python scripts/index_results.py
```

**Step 2: Test diff**

```bash
python scripts/diff_results.py r5d-p0-20260310-140340 r5d-p05-20260310-141433
```

---

## P4.4: Commit P4 Component

```bash
git add scripts/index_results.py scripts/diff_results.py
git add results/RESULTS_INDEX.json results/diff_*.json
git commit -m "feat(automation): P4 results index and diff with index-based lookup

- index_results.py: Scan results/ → RESULTS_INDEX.json
- diff_results.py: Read index first, locate result files by run_id
- No glob/file search - uses RESULTS_INDEX.json as source of truth
- Supports explicit two-run comparison

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

# Phase Docs: Documentation

## Docs.1: Create Quick Start Guide

**Files:**
- Create: `docs/AUTOMATION_README.md`

**Step 1: Write README**

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
# MVP: One family only
contract_families:
  - "ANN"
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

### Update Contract Coverage

```bash
# 1. Update VALIDATION_MATRIX.json from new results
python scripts/populate_validation_matrix.py

# 2. Regenerate CONTRACT_COVERAGE_INDEX.json
python scripts/generate_contract_coverage.py
```

## Components

| Component | Script | Purpose | Input | Output |
|-----------|--------|---------|-------|--------|
| P1 | `bootstrap_capability_registry.py` | Scan adapter for operations | adapter code | `capabilities/*_capabilities.json` |
| P2 | `populate_validation_matrix.py` | Extract validations from results | result files | `VALIDATION_MATRIX.json` |
| P2 | `generate_contract_coverage.py` | Build coverage index | contracts + matrix | `CONTRACT_COVERAGE_INDEX.json` |
| P3 | `bootstrap_campaign.py` | Generate campaign skeletons | config.yaml | 8 artifacts |
| P4 | `index_results.py` | Index all result files | results/ | `RESULTS_INDEX.json` |
| P4 | `diff_results.py` | Compare two runs | RESULTS_INDEX + run_ids | diff_*.json |

## File Structure

```
capabilities/              # P1: Capability registries
├── *_capabilities.json
contracts/
├── CONTRACT_COVERAGE_INDEX.json  # P2: Auto-generated coverage
├── VALIDATION_MATRIX.json        # P2: Source of truth for validations
campaigns/                 # P3: Campaign configs
└── {name}/
    ├── config.yaml
    └── bootstrap_manifest.json
results/
├── RESULTS_INDEX.json     # P4: Results index (source of truth)
└── diff_*.json            # P4: Diff outputs
scripts/
├── bootstrap_capability_registry.py
├── bootstrap_campaign.py
├── populate_validation_matrix.py
├── generate_contract_coverage.py
├── index_results.py
└── diff_results.py
```

## Design Document

See `docs/plans/2026-03-10-AUTOMATION_ACCELERATION_MVP.md` for full design.
```

---

## Docs.2: Commit Documentation

```bash
git add docs/AUTOMATION_README.md
git commit -m "docs(automation): add automation quick start guide

- Quick start for all 4 components
- Component reference table
- Update workflows for registries and coverage
- File structure overview

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

# Summary

## Components Delivered

| Component | Deliverables | Commit Strategy |
|-----------|--------------|-----------------|
| **P1** | Capability registries + bootstrap script | Single commit per component |
| **P2** | Coverage index + validation matrix + generators | Single commit per component |
| **P3** | Campaign bootstrap + 8 artifacts | Single commit per component |
| **P4** | Index + diff scripts | Single commit per component |
| **Docs** | Quick start guide | Single commit |

## Key Fixes Applied

1. **Commit granularity**: Per-component, not per-task
2. **P2 automation**: VALIDATION_MATRIX as source of truth, auto-generate coverage
3. **P3 fixes**: required_operations, python-safe slugs, single-family MVP
4. **P4 diff**: Index-based lookup, not glob search
5. **P1 scan**: Execute dispatch priority, filter helpers

## Success Criteria

- New campaign bootstrapped with single command
- Results indexable and comparable
- Coverage auto-generated from validation matrix
- Campaign startup time reduced by 50-70%

---

**Plan Version**: 2.0 (Corrected)
**Date**: 2026-03-10
**Status**: READY FOR EXECUTION
