#!/usr/bin/env python3
"""Bootstrap a new campaign from YAML config.

Generates 8 skeleton artifacts for campaign development.

MVP: Supports one primary contract_family only.
File naming: Python-safe slugs (underscores, not hyphens).
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

MVP Note: This campaign focuses on the {contract_family} contract family.

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
- Contracts: `contracts/{family_dir}/{campaign_slug}_contracts.json`
- Results: `results/{{run_id}}.json`

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
    family_dir = primary_family.lower() if primary_family != "TODO" else "ann"
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
        family_dir=primary_family.lower() if primary_family != "TODO" else "ann",
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
        "contract_coverage_snapshot": config.get("input_regries", {}).get("contract_coverage")
    }

    manifest_path = config_path.parent / "bootstrap_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"Generated {len(artifacts)} artifacts + 1 manifest:")
    for a in artifacts:
        print(f"  - {a['type']}: {a['path']}")
    print(f"  - manifest: {manifest_path}")

    return 0


if __name__ == "__main__":
    exit(main())
