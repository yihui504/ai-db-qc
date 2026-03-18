#!/usr/bin/env python3
"""
Bug Evidence Chain Validator
==========================
Validates all discovered bugs with complete evidence chains.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"

def load_results(filepath: Path) -> Dict[str, Any]:
    """Load test results from JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_bug_count(result: Dict[str, Any]) -> int:
    """Count bugs in a result file."""
    if "test_results" not in result:
        return 0
    
    bug_count = 0
    for test_result in result["test_results"]:
        verdict = test_result.get("overall_verdict", "PASS")
        if verdict not in ["PASS", "MARGINAL"]:
            bug_count += 1
    return bug_count

def analyze_test_case(test_case: Dict[str, Any]) -> List[str]:
    """Analyze a test case and return list of failed checks."""
    failed_checks = []
    checks = test_case.get("checks", [])
    
    for check in checks:
        check_name = check.get("name", "")
        check_status = check.get("status", True)
        
        if not check_status:
            failed_checks.append(f"{check_name}: status={check_status}")
        
        # Check for empty error messages
        if "error" in check_name.lower() or "diagnostics" in check_name.lower():
            message = check.get("message", "")
            if not message:
                failed_checks.append(f"{check_name}: empty error message")
    
    return failed_checks

def generate_evidence_chain(database: str, contract: str, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate evidence chain for a contract."""
    evidence_chain = {
        "database": database,
        "contract": contract,
        "test_cases": []
    }
    
    for test_case in test_cases:
        name = test_case.get("name", "")
        verdict = test_case.get("verdict", "PASS")
        failed_checks = analyze_test_case(test_case)
        
        evidence_chain["test_cases"].append({
            "name": name,
            "verdict": verdict,
            "failed_checks": failed_checks,
            "is_bug": verdict not in ["PASS", "MARGINAL"]
        })
    
    return evidence_chain

def main():
    """Main validation function."""
    print("=" * 80)
    print("Bug Evidence Chain Validator")
    print("=" * 80)
    
    # Analyze all databases
    databases = ["milvus", "qdrant", "weaviate", "pgvector"]
    all_bugs = []
    
    for db in databases:
        print(f"\n{'='*60}")
        print(f"Analyzing {db.upper()}")
        print(f"{'='*60}")
        
        db_bugs = {
            "database": db,
            "bugs_by_contract": defaultdict(list)
        }
        
        # Schema evolution
        schema_file = RESULTS_DIR / "schema_evolution_2025_001" / f"{db}_schema_evolution_results.json"
        if schema_file.exists():
            schema_results = load_results(schema_file)
            if isinstance(schema_results, list):
                for test_result in schema_results:
                    contract_id = test_result.get("contract_id", "")
                    verdict = test_result.get("overall_verdict", "PASS")
                    if verdict not in ["PASS", "MARGINAL"]:
                        db_bugs["bugs_by_contract"][contract_id].append({
                            "verdict": verdict
                        })
        
        # Boundary tests
        boundary_file = RESULTS_DIR / "boundary_2025_001" / f"{db}_boundary_results.json"
        if boundary_file.exists():
            boundary_results = load_results(boundary_file)
            if isinstance(boundary_results, list):
                for test_result in boundary_results:
                    contract_id = test_result.get("contract_id", "")
                    verdict = test_result.get("overall_verdict", "PASS")
                    if verdict not in ["PASS", "MARGINAL"]:
                        db_bugs["bugs_by_contract"][contract_id].append({
                            "verdict": verdict
                        })
        
        # Stress tests
        stress_file = RESULTS_DIR / "stress_2025_001" / f"{db}_stress_results.json"
        if stress_file.exists():
            stress_results = load_results(stress_file)
            if isinstance(stress_results, list):
                for test_result in stress_results:
                    contract_id = test_result.get("contract_id", "")
                    verdict = test_result.get("overall_verdict", "PASS")
                    if verdict not in ["PASS", "MARGINAL"]:
                        db_bugs["bugs_by_contract"][contract_id].append({
                            "verdict": verdict
                        })
        
        # Calculate total bugs
        total_bugs = sum(len(bugs) for bugs in db_bugs["bugs_by_contract"].values())
        db_bugs["total_bugs"] = total_bugs
        
        all_bugs.append(db_bugs)
        
        # Print summary
        print(f"\n{db.upper()} Bug Summary:")
        print(f"  Total Bugs: {total_bugs}")
        for contract, bugs_list in db_bugs["bugs_by_contract"].items():
            if bugs_list:
                print(f"  {contract}: {len(bugs_list)} bug(s)")
                for bug in bugs_list:
                    verdict = bug.get('verdict', 'UNKNOWN') if isinstance(bug, dict) else 'UNKNOWN'
                    print(f"    - {verdict}")
    
    # Overall summary
    print(f"\n{'='*80}")
    print("OVERALL SUMMARY")
    print(f"{'='*80}")
    
    total_all_bugs = sum(db_bugs["total_bugs"] for db_bugs in all_bugs)
    print(f"\nTotal Bugs Across All Databases: {total_all_bugs}")
    
    for db_bugs in all_bugs:
        db_name = db_bugs["database"].upper()
        bug_count = db_bugs["total_bugs"]
        print(f"\n{db_name}: {bug_count} bugs")
    
    # Save validation report
    report = {
        "validation_date": "2026-03-17",
        "databases": all_bugs,
        "total_bugs": total_all_bugs,
        "validation_method": "Evidence chain tracing"
    }
    
    report_path = PROJECT_ROOT / "bug_validation_summary.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nValidation report saved to: {report_path}")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
