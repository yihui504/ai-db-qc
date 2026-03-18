#!/usr/bin/env python3
"""
Analyze cross-database test results and identify potential bugs.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict


def load_report(report_path: str) -> Dict:
    """Load a JSON report file."""
    with open(report_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_errors(report: Dict) -> List[Dict]:
    """Extract all errors from a report."""
    errors = []
    
    for test_case in report.get('test_cases', []):
        case_id = test_case.get('case_id', 'unknown')
        case_name = test_case.get('name', 'unknown')
        
        for db_result in test_case.get('database_results', []):
            database = db_result.get('database', 'unknown')
            
            for step in db_result.get('steps', []):
                if not step.get('success', True):
                    errors.append({
                        'case_id': case_id,
                        'case_name': case_name,
                        'database': database,
                        'step': step.get('step', 0),
                        'operation': step.get('operation', 'unknown'),
                        'error': step.get('error', 'Unknown error'),
                        'params': step.get('params', {})
                    })
    
    return errors


def analyze_differences(report: Dict) -> List[Dict]:
    """Extract cross-database differences from a report."""
    differences = []
    
    for test_case in report.get('test_cases', []):
        case_id = test_case.get('case_id', 'unknown')
        case_name = test_case.get('name', 'unknown')
        
        comparison = test_case.get('cross_database_comparison', {})
        if comparison.get('has_differences', False):
            differences.append({
                'case_id': case_id,
                'case_name': case_name,
                'description': comparison.get('description', ''),
                'details': comparison.get('differences', []),
                'note': comparison.get('note', '')
            })
    
    return differences


def categorize_error(error: str) -> str:
    """Categorize an error by type."""
    error_lower = error.lower()
    
    if 'not loaded' in error_lower:
        return 'COLLECTION_NOT_LOADED'
    elif 'cannot parse' in error_lower or 'casted' in error_lower:
        return 'TYPE_CAST_ERROR'
    elif 'not found' in error_lower or "doesn't exist" in error_lower:
        return 'NOT_FOUND'
    elif 'format error' in error_lower or 'valid' in error_lower:
        return 'FORMAT_VALIDATION_ERROR'
    elif 'timeout' in error_lower:
        return 'TIMEOUT'
    elif 'connection' in error_lower:
        return 'CONNECTION_ERROR'
    else:
        return 'OTHER'


def identify_potential_bugs(errors: List[Dict], differences: List[Dict]) -> List[Dict]:
    """Identify potential bugs from errors and differences."""
    bugs = []
    
    # Group errors by case and operation
    error_groups = defaultdict(list)
    for error in errors:
        key = (error['case_id'], error['operation'])
        error_groups[key].append(error)
    
    # Analyze each error group
    for (case_id, operation), group in error_groups.items():
        databases_affected = set(e['database'] for e in group)
        error_types = set(categorize_error(e['error']) for e in group)
        
        # Potential bug indicators:
        # 1. Same error across multiple databases
        # 2. Type cast errors (likely API mismatch)
        # 3. Collection not loaded errors (likely lifecycle bug)
        
        for error in group:
            category = categorize_error(error['error'])
            
            # High priority: Type cast errors (API contract violation)
            if category == 'TYPE_CAST_ERROR':
                bugs.append({
                    'priority': 'HIGH',
                    'type': 'API_CONTRACT_VIOLATION',
                    'description': f"String ID used where Int64 expected in {error['database']}",
                    'details': error,
                    'suggestion': 'Adapter should convert string IDs to integers for Milvus'
                })
            
            # Medium priority: Collection not loaded
            elif category == 'COLLECTION_NOT_LOADED':
                bugs.append({
                    'priority': 'MEDIUM',
                    'type': 'LIFECYCLE_MANAGEMENT',
                    'description': f"Collection not loaded before search in {error['database']}",
                    'details': error,
                    'suggestion': 'Test should include explicit load() call before search'
                })
            
            # Low priority: Not found errors (may be expected)
            elif category == 'NOT_FOUND':
                bugs.append({
                    'priority': 'LOW',
                    'type': 'EXPECTED_BEHAVIOR',
                    'description': f"Resource not found in {error['database']}",
                    'details': error,
                    'suggestion': 'May be expected behavior after drop operations'
                })
    
    # Analyze differences for potential bugs
    for diff in differences:
        bugs.append({
            'priority': 'INFO',
            'type': 'CROSS_DB_DIFFERENCE',
            'description': f"{diff['case_name']} shows behavioral differences",
            'details': diff,
            'suggestion': 'Document as allowed difference or investigate further'
        })
    
    return bugs


def print_summary(report: Dict, report_name: str):
    """Print a summary of a report."""
    print(f"\n{'='*60}")
    print(f"Report: {report_name}")
    print(f"{'='*60}")
    
    test_cases = report.get('test_cases', [])
    databases = report.get('databases', [])
    
    print(f"Databases tested: {', '.join(databases)}")
    print(f"Test cases: {len(test_cases)}")
    
    total_steps = 0
    passed_steps = 0
    failed_steps = 0
    
    for test_case in test_cases:
        for db_result in test_case.get('database_results', []):
            steps = db_result.get('steps', [])
            total_steps += len(steps)
            for step in steps:
                if step.get('success', False):
                    passed_steps += 1
                else:
                    failed_steps += 1
    
    print(f"Total steps: {total_steps}")
    print(f"Passed: {passed_steps}")
    print(f"Failed: {failed_steps}")
    print(f"Success rate: {passed_steps/total_steps*100:.1f}%")


def main():
    """Main analysis function."""
    reports_dir = Path("c:/Users/11428/Desktop/ai-db-qc/runs/layer_i_real")
    
    report_files = [
        "r4-cross-db-real-db-r4-20260317-172254_report.json",
        "r6-cross-db-real-db-r6-20260317-172328_report.json",
        "r5d-cross-db-real-db-r5d-20260317-172426_report.json"
    ]
    
    all_errors = []
    all_differences = []
    all_bugs = []
    
    print("="*60)
    print("CROSS-DATABASE TEST RESULTS ANALYSIS")
    print("="*60)
    
    for report_file in report_files:
        report_path = reports_dir / report_file
        if not report_path.exists():
            print(f"Warning: {report_file} not found")
            continue
        
        report = load_report(str(report_path))
        print_summary(report, report_file)
        
        errors = analyze_errors(report)
        differences = analyze_differences(report)
        bugs = identify_potential_bugs(errors, differences)
        
        all_errors.extend(errors)
        all_differences.extend(differences)
        all_bugs.extend(bugs)
    
    # Print error summary
    print(f"\n{'='*60}")
    print("ERROR SUMMARY")
    print(f"{'='*60}")
    
    error_by_category = defaultdict(list)
    for error in all_errors:
        category = categorize_error(error['error'])
        error_by_category[category].append(error)
    
    for category, errors in sorted(error_by_category.items()):
        print(f"\n{category}: {len(errors)} errors")
        for error in errors[:3]:  # Show first 3 of each category
            print(f"  - {error['case_id']} ({error['database']}): {error['operation']}")
    
    # Print potential bugs
    print(f"\n{'='*60}")
    print("POTENTIAL BUGS IDENTIFIED")
    print(f"{'='*60}")
    
    high_priority = [b for b in all_bugs if b['priority'] == 'HIGH']
    medium_priority = [b for b in all_bugs if b['priority'] == 'MEDIUM']
    low_priority = [b for b in all_bugs if b['priority'] == 'LOW']
    info = [b for b in all_bugs if b['priority'] == 'INFO']
    
    print(f"\nHIGH PRIORITY ({len(high_priority)}):")
    for bug in high_priority[:5]:
        print(f"  [!] {bug['type']}: {bug['description']}")
        print(f"      Suggestion: {bug['suggestion']}")
    
    print(f"\nMEDIUM PRIORITY ({len(medium_priority)}):")
    for bug in medium_priority[:5]:
        print(f"  [*] {bug['type']}: {bug['description']}")
        print(f"      Suggestion: {bug['suggestion']}")
    
    print(f"\nLOW PRIORITY ({len(low_priority)}):")
    print(f"  Found {len(low_priority)} low-priority issues (mostly expected behaviors)")
    
    print(f"\nCROSS-DB DIFFERENCES ({len(info)}):")
    for bug in info[:5]:
        print(f"  [i] {bug['description']}")
    
    # Generate detailed report
    print(f"\n{'='*60}")
    print("GENERATING DETAILED REPORT...")
    print(f"{'='*60}")
    
    detailed_report = {
        'analysis_timestamp': '2026-03-17',
        'summary': {
            'total_errors': len(all_errors),
            'total_differences': len(all_differences),
            'high_priority_bugs': len(high_priority),
            'medium_priority_bugs': len(medium_priority),
            'low_priority_issues': len(low_priority)
        },
        'error_categories': {cat: len(errs) for cat, errs in error_by_category.items()},
        'high_priority_bugs': high_priority,
        'medium_priority_bugs': medium_priority,
        'all_errors': all_errors[:20]  # Include first 20 errors for detail
    }
    
    output_path = reports_dir / 'analysis_report.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(detailed_report, f, indent=2, ensure_ascii=False)
    
    print(f"Detailed report saved to: {output_path}")


if __name__ == '__main__':
    main()
