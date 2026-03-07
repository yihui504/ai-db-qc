"""Tests for the build_tables module."""

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def sample_summaries():
    """Create sample summary data for testing."""
    return [
        {
            "run_id": "run1",
            "run_tag": "baseline_real_runA",
            "adapter": "seekdb",
            "gate_enabled": True,
            "oracle_enabled": True,
            "triage_mode": "semantic",
            "milvus_available": True,
            "total_cases": 100,
            "total_executed": 95,
            "illegal_cases": 20,
            "legal_cases": 80,
            "precondition_pass_count": 85,
            "precondition_fail_count": 10,
            "observed_success_count": 70,
            "observed_failure_count": 15,
            "type1_count": 2,
            "type2_count": 5,
            "type2_precondition_failed_count": 3,
            "type3_count": 1,
            "type4_count": 2,
            "non_bug_count": 85,
            "oracle_fail_count": 2,
            "oracle_eval_count": 50,
            "precondition_pass_rate": 0.85,
            "type2_share_among_illegal_failures": 0.25,
            "type4_share_among_oracle_evaluable": 0.04,
            "non_bug_share": 0.85,
            "gate_filtered_share": 0.10
        },
        {
            "run_id": "run2",
            "run_tag": "no_gate_real",
            "adapter": "seekdb",
            "gate_enabled": False,
            "oracle_enabled": True,
            "triage_mode": "semantic",
            "milvus_available": True,
            "total_cases": 100,
            "total_executed": 100,
            "illegal_cases": 20,
            "legal_cases": 80,
            "precondition_pass_count": 80,
            "precondition_fail_count": 20,
            "observed_success_count": 70,
            "observed_failure_count": 20,
            "type1_count": 2,
            "type2_count": 8,
            "type2_precondition_failed_count": 5,
            "type3_count": 2,
            "type4_count": 2,
            "non_bug_count": 82,
            "oracle_fail_count": 2,
            "oracle_eval_count": 55,
            "precondition_pass_rate": 0.80,
            "type2_share_among_illegal_failures": 0.40,
            "type4_share_among_oracle_evaluable": 0.036,
            "non_bug_share": 0.82,
            "gate_filtered_share": 0.20
        },
        {
            "run_id": "run3",
            "run_tag": "no_oracle_real",
            "adapter": "seekdb",
            "gate_enabled": True,
            "oracle_enabled": False,
            "triage_mode": "semantic",
            "milvus_available": True,
            "total_cases": 100,
            "total_executed": 95,
            "illegal_cases": 20,
            "legal_cases": 80,
            "precondition_pass_count": 85,
            "precondition_fail_count": 10,
            "observed_success_count": 70,
            "observed_failure_count": 15,
            "type1_count": 2,
            "type2_count": 5,
            "type2_precondition_failed_count": 3,
            "type3_count": 1,
            "type4_count": 3,
            "non_bug_count": 84,
            "oracle_fail_count": 0,
            "oracle_eval_count": 0,
            "precondition_pass_rate": 0.85,
            "type2_share_among_illegal_failures": 0.25,
            "type4_share_among_oracle_evaluable": 0.0,
            "non_bug_share": 0.84,
            "gate_filtered_share": 0.10
        },
        {
            "run_id": "run4",
            "run_tag": "naive_triage_real",
            "adapter": "seekdb",
            "gate_enabled": True,
            "oracle_enabled": True,
            "triage_mode": "naive",
            "milvus_available": False,
            "total_cases": 100,
            "total_executed": 95,
            "illegal_cases": 20,
            "legal_cases": 80,
            "precondition_pass_count": 85,
            "precondition_fail_count": 10,
            "observed_success_count": 70,
            "observed_failure_count": 15,
            "type1_count": 1,
            "type2_count": 3,
            "type2_precondition_failed_count": 2,
            "type3_count": 1,
            "type4_count": 2,
            "non_bug_count": 89,
            "oracle_fail_count": 2,
            "oracle_eval_count": 50,
            "precondition_pass_rate": 0.85,
            "type2_share_among_illegal_failures": 0.15,
            "type4_share_among_oracle_evaluable": 0.04,
            "non_bug_share": 0.89,
            "gate_filtered_share": 0.10
        },
        {
            "run_id": "run5",
            "run_tag": "baseline_mock",
            "adapter": "mock",
            "gate_enabled": True,
            "oracle_enabled": True,
            "triage_mode": "semantic",
            "milvus_available": True,
            "total_cases": 100,
            "total_executed": 95,
            "illegal_cases": 20,
            "legal_cases": 80,
            "precondition_pass_count": 85,
            "precondition_fail_count": 10,
            "observed_success_count": 70,
            "observed_failure_count": 15,
            "type1_count": 2,
            "type2_count": 5,
            "type2_precondition_failed_count": 3,
            "type3_count": 1,
            "type4_count": 2,
            "non_bug_count": 85,
            "oracle_fail_count": 2,
            "oracle_eval_count": 50,
            "precondition_pass_rate": 0.85,
            "type2_share_among_illegal_failures": 0.25,
            "type4_share_among_oracle_evaluable": 0.04,
            "non_bug_share": 0.85,
            "gate_filtered_share": 0.10
        }
    ]


@pytest.fixture
def summary_file(sample_summaries, tmp_path):
    """Create a temporary summary JSON file."""
    summary_path = tmp_path / "phase5_summary.json"
    with open(summary_path, "w") as f:
        json.dump(sample_summaries, f)
    return summary_path


def test_table1_main_comparison(sample_summaries):
    """Test table1_main_comparison structure and content."""
    from analysis.build_tables import table1_main_comparison

    result = table1_main_comparison(sample_summaries)

    # Check structure
    assert "headers" in result
    assert "rows" in result

    # Check headers
    expected_headers = [
        "Run", "Total", "Precond Pass", "Failures",
        "T1", "T2", "T2.PF", "T3", "T4", "Non-bug", "Oracle Fail"
    ]
    assert result["headers"] == expected_headers

    # Check number of rows
    assert len(result["rows"]) == len(sample_summaries)

    # Check first row content (baseline_real_runA)
    first_row = result["rows"][0]
    assert first_row[0] == "baseline_real_runA"  # Run
    assert first_row[1] == 100  # Total
    assert first_row[2] == 85  # Precond Pass
    assert first_row[3] == 15  # Failures
    assert first_row[4] == 2  # T1
    assert first_row[5] == 5  # T2
    assert first_row[6] == 3  # T2.PF
    assert first_row[7] == 1  # T3
    assert first_row[8] == 2  # T4
    assert first_row[9] == 85  # Non-bug
    assert first_row[10] == 2  # Oracle Fail


def test_table2_gate_effect(sample_summaries):
    """Test table2_gate_effect structure and content."""
    from analysis.build_tables import table2_gate_effect

    result = table2_gate_effect(sample_summaries)

    # Check structure
    assert "title" in result
    assert "comparison" in result
    assert "metrics" in result

    # Check title and comparison
    assert result["title"] == "Gate Effect Comparison"
    assert result["comparison"] == "baseline_real_runA vs no_gate_real"

    # Check metrics structure
    assert "baseline_real_runA" in result["metrics"]
    assert "no_gate_real" in result["metrics"]

    # Check specific metric values for baseline
    baseline_metrics = result["metrics"]["baseline_real_runA"]
    assert baseline_metrics["precondition_fail_count"] == 10
    assert baseline_metrics["type3_count"] == 1
    assert baseline_metrics["type4_count"] == 2
    assert baseline_metrics["type2_precondition_failed_count"] == 3
    assert baseline_metrics["non_bug_count"] == 85

    # Check specific metric values for no_gate
    no_gate_metrics = result["metrics"]["no_gate_real"]
    assert no_gate_metrics["precondition_fail_count"] == 20
    assert no_gate_metrics["type3_count"] == 2


def test_table3_oracle_effect(sample_summaries):
    """Test table3_oracle_effect structure and content."""
    from analysis.build_tables import table3_oracle_effect

    result = table3_oracle_effect(sample_summaries)

    # Check structure
    assert "title" in result
    assert "comparison" in result
    assert "metrics" in result

    # Check title and comparison
    assert result["title"] == "Oracle Effect Comparison"
    assert result["comparison"] == "baseline_real_runA vs no_oracle_real"

    # Check metrics structure
    assert "baseline_real_runA" in result["metrics"]
    assert "no_oracle_real" in result["metrics"]

    # Check specific metric values
    baseline_metrics = result["metrics"]["baseline_real_runA"]
    assert baseline_metrics["oracle_eval_count"] == 50
    assert baseline_metrics["oracle_fail_count"] == 2

    no_oracle_metrics = result["metrics"]["no_oracle_real"]
    assert no_oracle_metrics["oracle_eval_count"] == 0
    assert no_oracle_metrics["oracle_fail_count"] == 0


def test_table4_triage_effect(sample_summaries):
    """Test table4_triage_effect structure and content."""
    from analysis.build_tables import table4_triage_effect

    result = table4_triage_effect(sample_summaries)

    # Check structure
    assert "title" in result
    assert "comparison" in result
    assert "metrics" in result

    # Check title and comparison
    assert result["title"] == "Triage Effect Comparison"
    assert result["comparison"] == "baseline_real_runA vs naive_triage_real"

    # Check metrics structure
    assert "baseline_real_runA" in result["metrics"]
    assert "naive_triage_real" in result["metrics"]

    # Check specific metric values
    baseline_metrics = result["metrics"]["baseline_real_runA"]
    assert baseline_metrics["illegal_cases"] == 20
    assert baseline_metrics["type2_count"] == 5
    assert baseline_metrics["type2_share_among_illegal_failures"] == 0.25

    naive_metrics = result["metrics"]["naive_triage_real"]
    assert naive_metrics["type2_count"] == 3
    assert naive_metrics["type2_share_among_illegal_failures"] == 0.15


def test_table5_mock_vs_real(sample_summaries):
    """Test table5_mock_vs_real structure and content."""
    from analysis.build_tables import table5_mock_vs_real

    result = table5_mock_vs_real(sample_summaries)

    # Check structure
    assert "title" in result
    assert "comparison" in result
    assert "metrics" in result

    # Check title and comparison
    assert result["title"] == "Mock vs Real Comparison"
    assert result["comparison"] == "baseline_mock vs baseline_real_runA"

    # Check metrics structure
    assert "baseline_mock" in result["metrics"]
    assert "baseline_real_runA" in result["metrics"]

    # Check that all required metrics are present
    for config_name in ["baseline_mock", "baseline_real_runA"]:
        metrics = result["metrics"][config_name]
        assert "total_cases" in metrics
        assert "precondition_pass_count" in metrics
        assert "observed_failure_count" in metrics
        assert "type1_count" in metrics
        assert "type2_count" in metrics
        assert "type2_precondition_failed_count" in metrics
        assert "type3_count" in metrics
        assert "type4_count" in metrics
        assert "non_bug_count" in metrics


def test_load_summaries(summary_file):
    """Test load_summaries function."""
    from analysis.build_tables import load_summaries

    summaries = load_summaries(summary_file)

    # Check that we loaded the correct number of summaries
    assert len(summaries) == 5

    # Check content of first summary
    assert summaries[0]["run_tag"] == "baseline_real_runA"
    assert summaries[0]["total_cases"] == 100


def test_write_all_tables_markdown(sample_summaries, tmp_path):
    """Test write_all_tables_markdown function."""
    from analysis.build_tables import (
        table1_main_comparison,
        table2_gate_effect,
        table3_oracle_effect,
        table4_triage_effect,
        table5_mock_vs_real,
        write_all_tables_markdown
    )

    # Generate tables
    tables = {
        "table1": table1_main_comparison(sample_summaries),
        "table2": table2_gate_effect(sample_summaries),
        "table3": table3_oracle_effect(sample_summaries),
        "table4": table4_triage_effect(sample_summaries),
        "table5": table5_mock_vs_real(sample_summaries)
    }

    # Write markdown file
    output_path = tmp_path / "comparison_tables.md"
    write_all_tables_markdown(tables, output_path)

    # Check file exists
    assert output_path.exists()

    # Check file content
    content = output_path.read_text()
    assert "# Comparison Tables" in content
    assert "## Table 1: Main Configuration Comparison" in content
    assert "## Table 2: Gate Effect Comparison" in content
    assert "## Table 3: Oracle Effect Comparison" in content
    assert "## Table 4: Triage Effect Comparison" in content
    assert "## Table 5: Mock vs Real Comparison" in content


def test_write_table_csvs(sample_summaries, tmp_path):
    """Test write_table_csvs function."""
    from analysis.build_tables import (
        table1_main_comparison,
        table2_gate_effect,
        table3_oracle_effect,
        table4_triage_effect,
        table5_mock_vs_real,
        write_table_csvs
    )

    # Generate tables
    tables = {
        "table1": table1_main_comparison(sample_summaries),
        "table2": table2_gate_effect(sample_summaries),
        "table3": table3_oracle_effect(sample_summaries),
        "table4": table4_triage_effect(sample_summaries),
        "table5": table5_mock_vs_real(sample_summaries)
    }

    # Write CSV files
    output_dir = tmp_path / "csv_output"
    write_table_csvs(tables, output_dir)

    # Check directory exists
    assert output_dir.exists()

    # Check that CSV files were created
    assert (output_dir / "table1_main_comparison.csv").exists()
    assert (output_dir / "table2_gate_effect_comparison.csv").exists()
    assert (output_dir / "table3_oracle_effect_comparison.csv").exists()
    assert (output_dir / "table4_triage_effect_comparison.csv").exists()
    assert (output_dir / "table5_mock_vs_real_comparison.csv").exists()
