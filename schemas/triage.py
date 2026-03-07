"""Triage result schema (separate from execution result)."""

from pydantic import BaseModel

from schemas.common import BugType, InputValidity, ObservedOutcome


class TriageResult(BaseModel):
    """Result of triage classification."""

    case_id: str
    run_id: str
    final_type: BugType
    input_validity: InputValidity
    observed_outcome: ObservedOutcome
    precondition_pass: bool  # CRITICAL for red-line
    rationale: str
