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
            db_family = database_str
            db_version = "unknown"

        return {
            "run_id": data.get("run_id"),
            "campaign": data.get("campaign"),
            "campaign_id": data.get("campaign_id"),
            "database_family": db_family,
            "db_version": db_version,
            "timestamp": data.get("timestamp"),
            "results": data.get("results", [])
        }
    except Exception as e:
        print(f"Warning: Could not parse {result_path}: {e}")
        return None


def main():
    # Result files to process
    result_files = [
        # R5B Index Lifecycle
        "results/r5b_lifecycle_20260310-124135.json",
        # R5D Schema Evolution
        "results/r5d_p0_20260310-140345.json",
        "results/r5d_p05_20260310-141439.json",
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

    return 0


if __name__ == "__main__":
    exit(main())
