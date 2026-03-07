"""Tests for EvidenceWriter."""

import json
import tempfile
from pathlib import Path
from shutil import rmtree

import pytest

from evidence.writer import EvidenceWriter
from schemas.case import TestCase
from schemas.common import OperationType, InputValidity, ObservedOutcome, BugType
from schemas.result import ExecutionResult, GateTrace
from schemas.triage import TriageResult


class TestEvidenceWriter:
    """Test EvidenceWriter functionality."""

    def setup_method(self):
        """Set up temp directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.writer = EvidenceWriter()

    def teardown_method(self):
        """Clean up temp directory."""
        rmtree(self.temp_dir, ignore_errors=True)

    def test_create_run_dir(self):
        """Test run directory creation."""
        run_dir = self.writer.create_run_dir("test-run", base_path=self.temp_dir)
        assert run_dir.exists()
        assert run_dir.name == "test-run"
        assert (run_dir / "test-run").exists() is False  # Not nested

    def test_create_run_dir_creates_parents(self):
        """Test run directory creation with parent directories."""
        run_dir = self.writer.create_run_dir("nested/test-run", base_path=self.temp_dir)
        assert run_dir.exists()
        assert run_dir.name == "test-run"

    def test_write_run_metadata(self):
        """Test run metadata writing."""
        run_dir = Path(self.temp_dir) / "test-run"
        run_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "run_id": "test-run",
            "timestamp": "2026-03-07T12:00:00",
            "case_count": 10
        }

        self.writer._write_run_metadata(run_dir, metadata)

        metadata_file = run_dir / "run_metadata.json"
        assert metadata_file.exists()

        with open(metadata_file) as f:
            loaded = json.load(f)

        assert loaded["run_id"] == "test-run"
        assert loaded["case_count"] == 10

    def test_write_cases(self):
        """Test cases writing as JSONL."""
        run_dir = Path(self.temp_dir) / "test-run"
        run_dir.mkdir(parents=True, exist_ok=True)

        cases = [
            TestCase(
                case_id="case-1",
                operation=OperationType.SEARCH,
                params={"top_k": 10},
                expected_validity=InputValidity.LEGAL,
                required_preconditions=[]
            ),
            TestCase(
                case_id="case-2",
                operation=OperationType.INSERT,
                params={"vectors": []},
                expected_validity=InputValidity.ILLEGAL,
                required_preconditions=["collection_exists"]
            )
        ]

        self.writer._write_cases(run_dir, cases)

        cases_file = run_dir / "cases.jsonl"
        assert cases_file.exists()

        with open(cases_file) as f:
            lines = f.readlines()

        assert len(lines) == 2

        # Verify first case
        case1 = json.loads(lines[0])
        assert case1["case_id"] == "case-1"
        assert case1["operation"] == "search"

        # Verify second case
        case2 = json.loads(lines[1])
        assert case2["case_id"] == "case-2"
        assert case2["operation"] == "insert"

    def test_write_execution_results(self):
        """Test execution results writing as JSONL."""
        run_dir = Path(self.temp_dir) / "test-run"
        run_dir.mkdir(parents=True, exist_ok=True)

        results = [
            ExecutionResult(
                run_id="run-1",
                case_id="case-1",
                adapter_name="MockAdapter",
                request={"operation": "search"},
                response={"status": "success"},
                observed_outcome=ObservedOutcome.SUCCESS,
                latency_ms=10.0,
                precondition_pass=True,
                gate_trace=[]
            ),
            ExecutionResult(
                run_id="run-1",
                case_id="case-2",
                adapter_name="MockAdapter",
                request={"operation": "insert"},
                response={"status": "error"},
                observed_outcome=ObservedOutcome.FAILURE,
                error_message="Invalid parameter",
                latency_ms=5.0,
                precondition_pass=False,
                gate_trace=[GateTrace(precondition_name="collection_exists", check_type="runtime", passed=False)]
            )
        ]

        self.writer._write_execution_results(run_dir, results)

        results_file = run_dir / "execution_results.jsonl"
        assert results_file.exists()

        with open(results_file) as f:
            lines = f.readlines()

        assert len(lines) == 2

        # Verify first result
        result1 = json.loads(lines[0])
        assert result1["case_id"] == "case-1"
        assert result1["observed_outcome"] == "success"

        # Verify second result
        result2 = json.loads(lines[1])
        assert result2["case_id"] == "case-2"
        assert result2["observed_outcome"] == "failure"
        assert result2["error_message"] == "Invalid parameter"

    def test_write_triage_report_filters_none(self):
        """Test triage report filters out None values (not bugs)."""
        run_dir = Path(self.temp_dir) / "test-run"
        run_dir.mkdir(parents=True, exist_ok=True)

        triage_results = [
            TriageResult(
                case_id="case-1",
                run_id="run-1",
                final_type=BugType.TYPE_1,
                input_validity=InputValidity.ILLEGAL.value,
                observed_outcome=ObservedOutcome.SUCCESS.value,
                precondition_pass=True,
                rationale="Illegal succeeded"
            ),
            None,  # Not a bug
            TriageResult(
                case_id="case-3",
                run_id="run-1",
                final_type=BugType.TYPE_3,
                input_validity=InputValidity.LEGAL.value,
                observed_outcome=ObservedOutcome.FAILURE.value,
                precondition_pass=True,
                rationale="Legal failed"
            ),
            None  # Not a bug
        ]

        self.writer._write_triage_report(run_dir, triage_results)

        report_file = run_dir / "triage_report.json"
        assert report_file.exists()

        with open(report_file) as f:
            bugs = json.load(f)

        # Only 2 bugs (None values filtered out)
        assert len(bugs) == 2
        assert bugs[0]["case_id"] == "case-1"
        assert bugs[1]["case_id"] == "case-3"

    def test_write_all_creates_all_files(self):
        """Test write_all creates all evidence files."""
        run_dir = Path(self.temp_dir) / "test-run"
        run_dir.mkdir(parents=True, exist_ok=True)

        cases = [
            TestCase(
                case_id="case-1",
                operation=OperationType.SEARCH,
                params={},
                expected_validity=InputValidity.LEGAL
            )
        ]

        results = [
            ExecutionResult(
                run_id="run-1",
                case_id="case-1",
                adapter_name="MockAdapter",
                request={},
                response={},
                observed_outcome=ObservedOutcome.SUCCESS,
                latency_ms=10.0,
                precondition_pass=True,
                gate_trace=[]
            )
        ]

        triage_results = [None]  # No bugs

        metadata = {"run_id": "test-run", "case_count": 1}

        self.writer.write_all(run_dir, metadata, cases, results, triage_results)

        # Verify all files created
        assert (run_dir / "run_metadata.json").exists()
        assert (run_dir / "cases.jsonl").exists()
        assert (run_dir / "execution_results.jsonl").exists()
        assert (run_dir / "triage_report.json").exists()

    def test_triage_report_empty_when_no_bugs(self):
        """Test triage report is empty list when no bugs found."""
        run_dir = Path(self.temp_dir) / "test-run"
        run_dir.mkdir(parents=True, exist_ok=True)

        triage_results = [None, None, None]  # All not bugs

        self.writer._write_triage_report(run_dir, triage_results)

        report_file = run_dir / "triage_report.json"
        assert report_file.exists()

        with open(report_file) as f:
            bugs = json.load(f)

        assert bugs == []
