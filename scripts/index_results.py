#!/usr/bin/env python3
"""Index result files in results/ directory.

Generates RESULTS_INDEX.json as the lookup table for result files by run_id.
This is the source of truth for locating result files - no glob needed.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


def parse_result_metadata(result_path: Path) -> Optional[Dict[str, Any]]:
    """Extract metadata from a result file.

    Args:
        result_path: Path to result JSON file

    Returns:
        Metadata dict or None if parsing fails
    """
    try:
        data = json.loads(result_path.read_text())

        # Extract database info
        database_str = data.get("database", "")
        if " " in database_str:
            db_family, db_version = database_str.split(" ", 1)
        else:
            db_family = database_str or "unknown"
            db_version = "unknown"

        # Get summary
        summary = data.get("summary", {})

        return {
            "run_id": data.get("run_id", result_path.stem),
            "result_file": str(result_path),
            "timestamp": data.get("timestamp"),
            "database_family": db_family,
            "db_version": db_version,
            "mode": data.get("mode", "UNKNOWN"),
            "campaign": data.get("campaign"),
            "total_cases": summary.get("total", 0),
            "classifications": summary.get("by_classification", {}),
            "file_size_bytes": result_path.stat().st_size
        }
    except Exception as e:
        print(f"Warning: Could not parse {result_path}: {e}")
        return None


def index_results(results_dir: Path = None) -> List[Dict[str, Any]]:
    """Scan results/ directory and build index.

    Args:
        results_dir: Path to results directory (default: results/)

    Returns:
        List of index entries sorted by timestamp (newest first)
    """
    if results_dir is None:
        results_dir = Path("results")

    if not results_dir.exists():
        print(f"Error: Results directory not found: {results_dir}")
        return []

    index_entries = []

    for result_file in results_dir.glob("*.json"):
        metadata = parse_result_metadata(result_file)
        if metadata:
            index_entries.append(metadata)

    # Sort by timestamp (newest first), then by run_id
    index_entries.sort(
        key=lambda x: (x.get("timestamp") or "", x.get("run_id")),
        reverse=True
    )

    return index_entries


def main():
    """Generate RESULTS_INDEX.json."""
    entries = index_results()

    if not entries:
        print("No result files found to index")
        return 1

    # Build index
    index = {
        "last_updated": datetime.now().isoformat(),
        "total_runs": len(entries),
        "entries": entries
    }

    # Write index
    output_path = Path("results/RESULTS_INDEX.json")
    output_path.write_text(json.dumps(index, indent=2))

    print(f"Generated: {output_path}")
    print(f"Total runs indexed: {len(entries)}")

    # Summary by campaign
    campaigns: Dict[str, int] = {}
    for e in entries:
        campaign = e.get("campaign") or "unknown"
        campaigns[campaign] = campaigns.get(campaign, 0) + 1

    print("\nRuns by campaign:")
    for campaign in sorted(campaigns.keys()):
        print(f"  {campaign}: {campaigns[campaign]}")

    # Summary by database
    databases: Dict[str, int] = {}
    for e in entries:
        db = f"{e.get('database_family')} {e.get('db_version')}"
        databases[db] = databases.get(db, 0) + 1

    print("\nRuns by database:")
    for db in sorted(databases.keys()):
        print(f"  {db}: {databases[db]}")

    return 0


if __name__ == "__main__":
    exit(main())
