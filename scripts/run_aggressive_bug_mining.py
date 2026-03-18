#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aggressive Bug Mining Campaign Runner
===================================
Runs the comprehensive bug mining campaign for schema, boundary, and stress testing.

Usage:
    python scripts/run_aggressive_bug_mining.py --db milvus
    python scripts/run_aggressive_bug_mining.py --db all
    python scripts/run_aggressive_bug_mining.py --config campaigns/aggressive_bug_mining.yaml
"""

import argparse
import sys
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any
import json
import os

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.system("chcp 65001 > nul")

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Campaign runner
# ---------------------------------------------------------------------------

class CampaignRunner:
    """Runner for aggressive bug mining campaign."""

    def __init__(self, config_path: str):
        """Initialize campaign runner.

        Args:
            config_path: Path to campaign config file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.results = {
            "campaign_id": self.config.get("campaign_id", "unknown"),
            "start_time": time.time(),
            "phases": {},
            "summary": {}
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load campaign configuration.

        Returns:
            Configuration dictionary
        """
        with open(self.config_path, "r") as f:
            import yaml
            return yaml.safe_load(f)

    def run(self, databases: List[str]) -> Dict[str, Any]:
        """Run the campaign on specified databases.

        Args:
            databases: List of databases to test

        Returns:
            Campaign results
        """
        print(f"\n{'='*80}")
        print(f"AGGRESSIVE BUG MINING CAMPAIGN")
        print(f"{'='*80}")
        print(f"Campaign ID: {self.config.get('campaign_id')}")
        print(f"Databases: {', '.join(databases)}")
        print(f"{'='*80}\n")

        # Phase 1: Schema Evolution Testing
        if self.config.get("schema_evolution_testing", {}).get("enabled", False):
            print(f"\n{'#'*80}")
            print(f"# PHASE 1: Schema Evolution Testing")
            print(f"{'#'*80}\n")

            schema_script = PROJECT_ROOT / "scripts/run_schema_evolution.py"
            if schema_script.exists():
                self._run_phase("schema_evolution", schema_script, databases)
            else:
                print(f"Warning: Schema evolution script not found: {schema_script}")

        # Phase 2: Boundary Testing
        if self.config.get("boundary_testing", {}).get("enabled", False):
            print(f"\n{'#'*80}")
            print(f"# PHASE 2: Boundary Condition Testing")
            print(f"{'#'*80}\n")

            boundary_script = PROJECT_ROOT / "scripts/run_boundary_tests.py"
            if boundary_script.exists():
                self._run_phase("boundary", boundary_script, databases)
            else:
                print(f"Warning: Boundary testing script not found: {boundary_script}")

        # Phase 3: Stress Testing
        if self.config.get("stress_testing", {}).get("enabled", False):
            print(f"\n{'#'*80}")
            print(f"# PHASE 3: Stress Testing")
            print(f"{'#'*80}\n")

            stress_script = PROJECT_ROOT / "scripts/run_stress_tests.py"
            if stress_script.exists():
                self._run_phase("stress", stress_script, databases)
            else:
                print(f"Warning: Stress testing script not found: {stress_script}")

        # Phase 4: Targeted Fuzzing
        if self.config.get("targeted_fuzzing", {}).get("enabled", False):
            print(f"\n{'#'*80}")
            print(f"# PHASE 4: Targeted Fuzzing")
            print(f"{'#'*80}\n")
            print("Targeted fuzzing can be run separately using fuzzer modules.")
            print("See: casegen/fuzzing/targeted_fuzzer.py, schema_fuzzer.py")

        # Phase 5: Integration Testing
        if self.config.get("integration_testing", {}).get("enabled", False):
            print(f"\n{'#'*80}")
            print(f"# PHASE 5: Integration Testing")
            print(f"{'#'*80}\n")
            print("Integration testing combines schema, boundary, and stress tests.")
            print("This can be customized based on specific scenarios.")

        # Generate summary
        self._generate_summary()

        # Save results
        self._save_results()

        return self.results

    def _run_phase(
        self,
        phase_name: str,
        script_path: Path,
        databases: List[str]
    ):
        """Run a testing phase.

        Args:
            phase_name: Name of the phase
            script_path: Path to test script
            databases: List of databases to test
        """
        phase_results = {"databases": {}}
        self.results["phases"][phase_name] = phase_results

        for db in databases:
            print(f"\n{'-'*60}")
            print(f"Testing {db.upper()} - {phase_name}")
            print(f"{'-'*60}\n")

            output_dir = PROJECT_ROOT / "results" / f"{phase_name}_2025_001"
            output_file = output_dir / f"{db}_{phase_name}_results.json"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Run the script
            cmd = [
                sys.executable,
                str(script_path),
                "--db", db,
                "--output", str(output_file)
            ]

            print(f"Running: {' '.join(cmd)}")

            try:
                result = subprocess.run(
                    cmd,
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=3600  # 1 hour max per phase
                )

                print(result.stdout)
                if result.stderr:
                    print(f"STDERR: {result.stderr}")

                phase_results["databases"][db] = {
                    "exit_code": result.returncode,
                    "success": result.returncode == 0,
                    "output_file": str(output_file) if output_file.exists() else None
                }

                # Load results if available
                if output_file.exists():
                    try:
                        with open(output_file, "r") as f:
                            phase_results["databases"][db]["test_results"] = json.load(f)
                    except Exception as e:
                        phase_results["databases"][db]["load_error"] = str(e)

            except subprocess.TimeoutExpired:
                print(f"\n✗ Timeout testing {db}")
                phase_results["databases"][db] = {
                    "exit_code": -1,
                    "success": False,
                    "error": "timeout"
                }
            except Exception as e:
                print(f"\n✗ Error testing {db}: {e}")
                phase_results["databases"][db] = {
                    "exit_code": -1,
                    "success": False,
                    "error": str(e)
                }

    def _generate_summary(self):
        """Generate campaign summary."""
        print(f"\n{'='*80}")
        print(f"CAMPAIGN SUMMARY")
        print(f"{'='*80}\n")

        summary = {
            "total_phases": len(self.results["phases"]),
            "phases_completed": 0,
            "total_bugs": 0,
            "critical_bugs": 0,
            "bugs_by_phase": {},
            "bugs_by_db": {},
            "bugs_by_contract": {}
        }

        for phase_name, phase_data in self.results["phases"].items():
            summary["phases_completed"] += 1
            summary["bugs_by_phase"][phase_name] = 0

            for db, db_data in phase_data.get("databases", {}).items():
                if db_data.get("success", False):
                    test_results = db_data.get("test_results", [])

                    for test_result in test_results:
                        if isinstance(test_result, dict):
                            # Count bugs
                            verdict = test_result.get("overall_verdict", "")
                            if "BUG" in verdict or verdict in ["TYPE-1", "TYPE-2", "TYPE-3", "TYPE-4"]:
                                summary["total_bugs"] += 1
                                summary["bugs_by_phase"][phase_name] += 1
                                summary["bugs_by_db"][db] = summary["bugs_by_db"].get(db, 0) + 1

                                contract = test_result.get("contract_id", "unknown")
                                summary["bugs_by_contract"][contract] = summary["bugs_by_contract"].get(contract, 0) + 1

                                if "CRITICAL" in verdict.upper():
                                    summary["critical_bugs"] += 1

        self.results["summary"] = summary

        # Print summary
        print(f"Total Phases: {summary['total_phases']}")
        print(f"Phases Completed: {summary['phases_completed']}")
        print(f"Total Bugs Found: {summary['total_bugs']}")
        print(f"Critical Bugs: {summary['critical_bugs']}")

        print(f"\nBugs by Phase:")
        for phase, count in summary["bugs_by_phase"].items():
            print(f"  {phase}: {count}")

        print(f"\nBugs by Database:")
        for db, count in summary["bugs_by_db"].items():
            print(f"  {db}: {count}")

        print(f"\nBugs by Contract:")
        for contract, count in summary["bugs_by_contract"].items():
            print(f"  {contract}: {count}")

    def _save_results(self):
        """Save campaign results."""
        self.results["end_time"] = time.time()
        self.results["duration_seconds"] = self.results["end_time"] - self.results["start_time"]

        output_dir = PROJECT_ROOT / "results" / "aggressive_bug_mining_2025_001"
        output_dir.mkdir(parents=True, exist_ok=True)

        results_file = output_dir / "campaign_results.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\nCampaign results saved to: {results_file}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run aggressive bug mining campaign")
    parser.add_argument("--config", type=str,
                       default="campaigns/aggressive_bug_mining.yaml",
                       help="Path to campaign config file")
    parser.add_argument("--db", type=str, default="milvus",
                       choices=["milvus", "qdrant", "weaviate", "pgvector", "all"],
                       help="Database to test")
    args = parser.parse_args()

    # Determine databases
    if args.db == "all":
        databases = ["milvus", "qdrant", "weaviate", "pgvector"]
    else:
        databases = [args.db]

    # Load config
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    # Run campaign
    runner = CampaignRunner(str(config_path))
    results = runner.run(databases)

    # Exit with appropriate code
    total_bugs = results.get("summary", {}).get("total_bugs", 0)
    if total_bugs > 0:
        print(f"\n[SUCCESS] Campaign completed with {total_bugs} bugs found")
        sys.exit(0)
    else:
        print(f"\n[SUCCESS] Campaign completed successfully (no bugs found)")
        sys.exit(0)


if __name__ == "__main__":
    main()
