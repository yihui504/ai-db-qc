"""Execution result schema."""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, TYPE_CHECKING

from schemas.common import ObservedOutcome, GateTrace

if TYPE_CHECKING:
    from schemas.triage import TriageResult


class OracleResult(BaseModel):
    """Result from an oracle validation check."""

    oracle_id: str
    passed: bool
    explanation: str = ""
    metrics: Dict[str, Any] = Field(default_factory=dict)  # Optional metrics
    expected_relation: str = ""  # Expected relationship (e.g., "filtered <= unfiltered")
    observed_relation: str = ""  # Observed relationship (e.g., "filtered (5) > unfiltered (3)")


class ExecutionResult(BaseModel):
    """Result of executing a test case."""

    run_id: str
    case_id: str
    adapter_name: str
    request: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    observed_outcome: ObservedOutcome
    error_message: Optional[str] = None
    latency_ms: float
    precondition_pass: bool  # CRITICAL for red-line
    gate_trace: List[GateTrace] = Field(default_factory=list)
    oracle_results: List[OracleResult] = Field(default_factory=list)
    snapshot_id: str = Field(default="", description="Runtime snapshot ID for this execution")
    triage_result: Optional["TriageResult"] = Field(default=None, description="Triage classification result")

    @property
    def observed_success(self) -> bool:
        """Convenience property: was the execution successful?"""
        return self.observed_outcome == ObservedOutcome.SUCCESS
