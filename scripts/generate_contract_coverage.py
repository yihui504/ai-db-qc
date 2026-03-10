#!/usr/bin/env python3
"""Generate contract coverage index from contracts + validation matrix.

Source of truth:
- Contract definitions: stable metadata (contract_id, family, statement)
- VALIDATION_MATRIX.json: dynamic validation status

Output:
- CONTRACT_COVERAGE_INDEX.json: Auto-generated merge

Manual input only:
- framework_level_candidate (in contract files)
- notes (can be overridden)
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime


def parse_individual_contract(contract_path: Path) -> List[Dict[str, Any]]:
    """Parse individual contract file (one contract per file)."""
    try:
        data = json.loads(contract_path.read_text())
        contract_id = data.get("contract_id")
        if not contract_id:
            return []

        return [{
            "contract_id": contract_id,
            "family": data.get("family", "UNKNOWN"),
            "statement": data.get("statement", ""),
            "semantic_area": data.get("scope", {}).get("semantic_area", "unknown"),
            "stable_metadata": {
                "maturity": data.get("metadata", {}).get("confidence", "unknown"),
                "intended_scope": data.get("scope", {}).get("databases", ["all"]),
                "framework_level_candidate": data.get("type") == "universal"
            }
        }]
    except Exception as e:
        print(f"Warning: Could not parse {contract_path}: {e}")
        return []


def parse_combined_contract_file(contract_path: Path, family: str) -> List[Dict[str, Any]]:
    """Parse combined contract file (multiple contracts in one file).

    Handles: lifecycle_contracts.json, schema_contracts.json
    """
    try:
        data = json.loads(contract_path.read_text())
        contracts = []

        # Check if it's a layered structure (lifecycle, schema)
        if "contract_layers" in data:
            # Extract contracts from layers
            for layer_name, layer_data in data.get("contract_layers", {}).items():
                if isinstance(layer_data, dict) and "contracts" in layer_data:
                    for contract in layer_data["contracts"]:
                        contracts.append({
                            "contract_id": contract.get("contract_id"),
                            "family": family,
                            "statement": contract.get("statement", ""),
                            "semantic_area": layer_name,
                            "stable_metadata": {
                                "maturity": contract.get("confidence", "unknown"),
                                "intended_scope": ["all"],  # Default for lifecycle
                                "framework_level_candidate": contract.get("milvus_verified", False) or
                                                          contract.get("framework_level_candidate", False)
                            }
                        })
        return contracts
    except Exception as e:
        print(f"Warning: Could not parse {contract_path}: {e}")
        return []


def load_contract_definitions() -> Dict[str, Dict[str, Any]]:
    """Load all contract definitions.

    Returns:
        Dict mapping contract_id to contract definition
    """
    contracts = {}

    # Individual contract files (ANN, Hybrid, some Index)
    individual_dirs = ["ann", "hybrid"]
    for family in individual_dirs:
        family_path = Path(f"contracts/{family}")
        if not family_path.exists():
            continue
        for contract_file in family_path.glob("*.json"):
            for contract in parse_individual_contract(contract_file):
                contracts[contract["contract_id"]] = contract

    # Combined index contract files
    index_path = Path("contracts/index")
    if index_path.exists():
        # Individual index contracts
        for contract_file in index_path.glob("idx-*.json"):
            for contract in parse_individual_contract(contract_file):
                contracts[contract["contract_id"]] = contract

        # Combined lifecycle contracts
        lifecycle_file = index_path / "lifecycle_contracts.json"
        if lifecycle_file.exists():
            for contract in parse_combined_contract_file(lifecycle_file, "INDEX"):
                contracts[contract["contract_id"]] = contract

    # Combined schema contracts
    schema_path = Path("contracts/schema")
    if schema_path.exists():
        # Individual schema contracts
        for contract_file in schema_path.glob("sch-*.json"):
            for contract in parse_individual_contract(contract_file):
                contracts[contract["contract_id"]] = contract

        # Combined schema contracts file
        schema_file = schema_path / "schema_contracts.json"
        if schema_file.exists():
            for contract in parse_combined_contract_file(schema_file, "SCHEMA"):
                contracts[contract["contract_id"]] = contract

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
) -> Tuple[str, str]:
    """Compute coverage_status and validation_level from validations.

    Args:
        validations: List of validation entries for a contract

    Returns:
        (coverage_status, validation_level)

    Mapping rules:
    - strongly_validated: All PASS, campaign-validated with strong evidence
    - partially_validated: Mix of PASS + non-bug classifications
    - observational_only: Expected behavior documented (EXPECTED_FAILURE, VERSION_GUARDED, OBSERVATION)
    - inconclusive: EXPERIMENT_DESIGN_ISSUE or truly inconclusive
    - unvalidated: No evidence
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

    # Observational: Expected failures or version-guarded behavior
    if any(c in ["EXPECTED_FAILURE", "VERSION_GUARDED"] for c in classifications):
        # These are framework-level expected behaviors
        return "observational_only", "campaign_validated"

    # Observational: Has OBSERVATION (documented behavior, not a bug)
    if "OBSERVATION" in classifications:
        # Check if also has PASS (mixed)
        if any(c == "PASS" for c in classifications):
            return "partially_validated", "campaign_validated"
        return "observational_only", "campaign_validated"

    # Partial: Mix of PASS + other non-bug classifications
    if "PASS" in classifications:
        return "partially_validated", "campaign_validated"

    # Default: has validations but unclear
    return "partially_validated", "campaign_validated"


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

    for contract_id, contract_def in sorted(contracts.items()):
        validations = validations_by_contract.get(contract_id, [])
        coverage_status, validation_level = compute_coverage_status(validations)

        entry = {
            "contract_id": contract_id,
            "family": contract_def["family"],
            "semantic_area": contract_def.get("semantic_area", "unknown"),
            "coverage_status": coverage_status,
            "validation_level": validation_level,
            "validated_in_campaigns": sorted(campaigns_by_contract.get(contract_id, set())),
            "case_evidence": case_evidence_by_contract.get(contract_id, []),
            "report_ref": None,  # TODO: Auto-detect
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

    # Print summary by family
    print("\nCoverage by family:")
    for family, counts in summary_by_family.items():
        print(f"  {family}: {sum(counts.values())} contracts")
        for status, count in sorted(counts.items()):
            print(f"    - {status}: {count}")

    return 0


if __name__ == "__main__":
    exit(generate_coverage_index())
