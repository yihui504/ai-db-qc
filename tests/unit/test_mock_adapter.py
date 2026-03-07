"""Unit tests for MockAdapter."""

import pytest
from adapters.mock import MockAdapter, ResponseMode, DiagnosticQuality
from schemas.common import ObservedOutcome
from schemas.result import OracleResult


def test_mock_adapter_success():
    """Test SUCCESS mode."""
    adapter = MockAdapter(ResponseMode.SUCCESS)
    response = adapter.execute({"operation": "search"})

    assert response["status"] == "success"
    assert "error" not in response or response.get("error") is None


def test_mock_adapter_failure():
    """Test FAILURE mode."""
    adapter = MockAdapter(ResponseMode.FAILURE, DiagnosticQuality.FULL)
    response = adapter.execute({"operation": "search"})

    assert response["status"] == "error"
    assert "error" in response
    assert "parameter" in response.get("error_details", {})


def test_mock_adapter_diagnostic_quality():
    """Test diagnostic quality affects error messages."""
    # FULL quality
    adapter_full = MockAdapter(ResponseMode.FAILURE, DiagnosticQuality.FULL)
    response_full = adapter_full.execute({"operation": "search"})
    assert "parameter" in response_full.get("error_details", {})

    # PARTIAL quality
    adapter_partial = MockAdapter(ResponseMode.FAILURE, DiagnosticQuality.PARTIAL)
    response_partial = adapter_partial.execute({"operation": "search"})
    assert "parameter" not in response_partial.get("error_details", {})

    # NONE quality
    adapter_none = MockAdapter(ResponseMode.FAILURE, DiagnosticQuality.NONE)
    response_none = adapter_none.execute({"operation": "search"})
    assert response_none["error"] in ["Error", "error"]


def test_mock_adapter_crash():
    """Test CRASH mode."""
    adapter = MockAdapter(ResponseMode.CRASH)
    response = adapter.execute({"operation": "search"})

    assert response["status"] == "crash"


def test_mock_adapter_hang():
    """Test HANG mode."""
    adapter = MockAdapter(ResponseMode.HANG)
    response = adapter.execute({"operation": "search"})

    assert response["status"] == "hang"


def test_mock_adapter_timeout():
    """Test TIMEOUT mode."""
    adapter = MockAdapter(ResponseMode.TIMEOUT)
    response = adapter.execute({"operation": "search"})

    assert response["status"] == "timeout"


def test_mock_adapter_with_oracle_result():
    """Test mock adapter with oracle result for Type-4 simulation."""
    oracle = OracleResult(
        oracle_id="mock_oracle",
        passed=False,
        explanation="Simulated failure"
    )

    adapter = MockAdapter(
        ResponseMode.SUCCESS,
        mock_oracle_result=oracle
    )

    assert adapter.mock_oracle_result == oracle
    assert adapter.mock_oracle_result.passed is False
