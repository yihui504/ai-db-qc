"""Tests for run summarization module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from analysis.summarize_runs import (
    load_run_metadata,
    load_execution_results,
    load_triage_report,
    load_cases,
    summarize_single_run,
    summarize_all_runs,
    write_summary_json,
    write_summary_markdown,
)


@pytest.fixture
def mock_run_dir(tmp_path: Path) -> Path:
    """Create a mock run directory with test data."""
    run_dir = tmp_path / "test_run_001"
    run_dir.mkdir()

    # Create run_metadata.json
    metadata = {
        "run_id": "test_run_001",
        "run_tag": "test-tag",
        "adapter": "milvus",
        "gate_enabled": True,
        "oracle_enabled": True,
        "triage_mode": "full",
        "milvus_available": True,
    }
    with open(run_dir / "run_metadata.json", "w") as f:
        json.dump(metadata, f)

    # Create cases.jsonl
    cases = [
        {"case_id": "case1", "input_validity": "illegal", "operation": "search"},
        {"case_id": "case2", "input_validity": "illegal", "operation": "insert"},
        {"case_id": "case3", "input_validity": "legal", "operation": "search"},
        {"case_id": "case4", "input_validity": "legal", "operation": "insert"},
        {"case_id": "case5", "input_validity": "illegal", "operation": "delete"},
    ]
    with open(run_dir / "cases.jsonl", "w") as f:
        for case in cases:
            f.write(json.dumps(case) + "\n")

    # Create execution_results.jsonl
    results = [
        {
            "run_id": "test_run_001",
            "case_id": "case1",
            "adapter_name": "milvus",
            "request": {},
            "response": {},
            "observed_outcome": "failure",
            "precondition_pass": True,
            "oracle_results": [],
            "latency_ms": 100.0,
        },
        {
            "run_id": "test_run_001",
            "case_id": "case2",
            "adapter_name": "milvus",
            "request": {},
            "response": {},
            "observed_outcome": "failure",
            "precondition_pass": True,
            "oracle_results": [],
            "latency_ms": 150.0,
        },
        {
            "run_id": "test_run_001",
            "case_id": "case3",
            "adapter_name": "milvus",
            "request": {},
            "response": {},
            "observed_outcome": "success",
            "precondition_pass": True,
            "oracle_results": [],
            "latency_ms": 50.0,
        },
        {
            "run_id": "test_run_001",
            "case_id": "case4",
            "adapter_name": "milvus",
            "request": {},
            "response": {},
            "observed_outcome": "success",
            "precondition_pass": False,
            "oracle_results": [],
            "latency_ms": 75.0,
        },
        {
            "run_id": "test_run_001",
            "case_id": "case5",
            "adapter_name": "milvus",
            "request": {},
            "response": {},
            "observed_outcome": "failure",
            "precondition_pass": True,
            "oracle_results": [
                {"oracle_id": "test_oracle", "passed": False, "explanation": "Test failed"}
            ],
            "latency_ms": 200.0,
        },
    ]
    with open(run_dir / "execution_results.jsonl", "w") as f:
        for result in results:
            f.write(json.dumps(result) + "\n")

    # Create triage_report.json
    triage = [
        {
            "case_id": "case1",
            "run_id": "test_run_001",
            "final_type": "type-2",
            "input_validity": "illegal",
            "observed_outcome": "failure",
            "precondition_pass": True,
            "rationale": "Illegal input caused failure",
        },
        {
            "case_id": "case2",
            "run_id": "test_run_001",
            "final_type": "type-1",
            "input_validity": "illegal",
            "observed_outcome": "failure",
            "precondition_pass": True,
            "rationale": "Crash on illegal input",
        },
        {
            "case_id": "case5",
            "run_id": "test_run_001",
            "final_type": "type-4",
            "input_validity": "illegal",
            "observed_outcome": "failure",
            "precondition_pass": True,
            "rationale": "Oracle violation",
        },
    ]
    with open(run_dir / "triage_report.json", "w") as f:
        json.dump(triage, f)

    return run_dir


def test_summarize_single_run(mock_run_dir: Path) -> None:
    """Test summarizing a single run directory."""
    summary = summarize_single_run(mock_run_dir)

    # Verify run identification
    assert summary["run_id"] == "test_run_001"
    assert summary["run_tag"] == "test-tag"
    assert summary["adapter"] == "milvus"
    assert summary["gate_enabled"] is True
    assert summary["oracle_enabled"] is True
    assert summary["triage_mode"] == "full"
    assert summary["milvus_available"] is True

    # Verify raw counts
    assert summary["total_cases"] == 5
    assert summary["total_executed"] == 5
    assert summary["illegal_cases"] == 3  # case1, case2, case5
    assert summary["legal_cases"] == 2  # case3, case4
    assert summary["precondition_pass_count"] == 4  # all except case4
    assert summary["precondition_fail_count"] == 1  # case4
    assert summary["observed_success_count"] == 2  # case3, case4
    assert summary["observed_failure_count"] == 3  # case1, case2, case5

    # Verify bug type counts
    assert summary["type1_count"] == 1  # case2
    assert summary["type2_count"] == 1  # case1
    assert summary["type2_precondition_failed_count"] == 0
    assert summary["type3_count"] == 0
    assert summary["type4_count"] == 1  # case5
    assert summary["non_bug_count"] == 2  # case3, case4

    # Verify oracle counts
    assert summary["oracle_eval_count"] == 1  # case5 has oracle results
    assert summary["oracle_fail_count"] == 1  # case5 oracle failed

    # Verify derived metrics
    assert summary["precondition_pass_rate"] == 4 / 5
    assert summary["type2_share_among_illegal_failures"] == 1 / 3  # 1 type-2 out of 3 failures
    assert summary["type4_share_among_oracle_evaluable"] == 1 / 1  # 1 type-4 out of 1 oracle eval
    assert summary["non_bug_share"] == 2 / 5
    assert summary["gate_filtered_share"] == 1 / 5
