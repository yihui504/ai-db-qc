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
from typing import Dict, List, Any, Optional


def parse_result_file(result_path: Path) -> Optional[Dict[str, Any]]:
    """Parse a single result file."""
    try:
        data = json.loads(result_path.read_text())

        # Extract database info
        database_str = data.get("database", "")
        if " " in database_str:
            db_family, db_version = database_str.split(" ", 1)
        else:
            db_family = database_str or "unknown"
            db_version = "unknown"

        # Extract campaign name (some files don't have campaign field)
        campaign = data.get("campaign")
        if not campaign:
            # Extract from filename
            if "ann_pilot" in result_path.name or "ann_discovery" in result_path.name:
                campaign = "ANN_PILOT"
            elif "hybrid_pilot" in result_path.name:
                campaign = "HYBRID_PILOT"
            else:
                campaign = result_path.stem

        # Handle different result structures
        results = data.get("results", [])
        # Normalize results - some use case_id, some use test_id
        for r in results:
            if "case_id" not in r and "test_id" in r:
                r["case_id"] = r["test_id"]

        return {
            "run_id": data.get("run_id", result_path.stem),
            "campaign": campaign,
            "campaign_id": data.get("campaign_id"),
            "database_family": db_family,
            "db_version": db_version,
            "timestamp": data.get("timestamp"),
            "results": results
        }
    except Exception as e:
        print(f"Warning: Could not parse {result_path}: {e}")
        return None


def main():
    # Result files to process - expanded to include ANN and Hybrid
    result_files = [
        # R5B Index Lifecycle
        "results/r5b_lifecycle_20260310-124135.json",
        # R5D Schema Evolution
        "results/r5d_p0_20260310-140345.json",
        "results/r5d_p05_20260310-141439.json",
        # ANN Discovery / Pilots
        "results/ann_discovery_20260310-001622.json",
        "results/ann_pilot_20260310-000124.json",
        # Hybrid Pilots
        "results/hybrid_pilot_20260310-004009.json",
        "results/hybrid_pilot_20260310-004155.json",
    ]

    validations = []

    for result_file in result_files:
        result_path = Path(result_file)
        if not result_path.exists():
            print(f"Warning: {result_file} not found, skipping")
            continue

        result = parse_result_file(result_path)
        if not result:
            continue

        # Process each result entry
        for case_result in result.get("results", []):
            validations.append({
                "database_family": result["database_family"],
                "db_version": result["db_version"],
                "contract_id": case_result.get("contract_id"),
                "status_scope": "case_level",
                "classification": case_result.get("oracle", {}).get("classification"),
                "case_id": case_result.get("case_id"),
                "result_file": result_file,
                "report_ref": None,  # TODO: Auto-detect
                "campaign": result["campaign"],
                "timestamp": result["timestamp"]
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

    # Summary by campaign
    campaigns = {}
    for v in validations:
        campaign = v["campaign"]
        if campaign not in campaigns:
            campaigns[campaign] = set()
        campaigns[campaign].add(v["contract_id"])

    print("\nValidations by campaign:")
    for campaign in sorted(c for c in campaigns.keys() if c):
        contracts = campaigns[campaign]
        print(f"  {campaign}: {len(contracts)} contract validations")

    return 0


if __name__ == "__main__":
    exit(main())
