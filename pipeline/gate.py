"""Precondition gate stub - separate from adapter."""

from __future__ import annotations

from enum import Enum
from typing import List

from schemas.case import TestCase
from schemas.common import GateTrace


class PreconditionMode(str, Enum):
    """Precheck evaluation modes."""
    ALL_PASS = "all_pass"
    ALL_FAIL = "all_fail"
    SELECTIVE = "selective"


class GateStub:
    """Minimal gate stub for precondition evaluation.

    Structurally separate from adapter - gate owns precondition_pass logic.
    """

    def __init__(self, mode: PreconditionMode = PreconditionMode.ALL_PASS):
        self.mode = mode

    def check(self, case: TestCase) -> tuple[bool, List[GateTrace]]:
        """
        Evaluate preconditions for a case.

        Returns:
            (precondition_pass, gate_trace)
        """
        gate_trace: List[GateTrace] = []

        if self.mode == PreconditionMode.ALL_PASS:
            # All preconditions pass
            for precond in case.required_preconditions:
                gate_trace.append(GateTrace(
                    precondition_name=precond,
                    passed=True,
                    reason="OK"
                ))
            return True, gate_trace

        elif self.mode == PreconditionMode.ALL_FAIL:
            # All preconditions fail
            for precond in case.required_preconditions:
                gate_trace.append(GateTrace(
                    precondition_name=precond,
                    passed=False,
                    reason="Not satisfied"
                ))
            return False, gate_trace

        else:  # SELECTIVE
            # Pass preconditions that are in the case's required list
            # This simulates partial satisfaction
            for precond in case.required_preconditions:
                # Simulate: some pass, some fail based on naming
                passed = "exists" in precond or "loaded" in precond
                gate_trace.append(GateTrace(
                    precondition_name=precond,
                    passed=passed,
                    reason="Satisfied" if passed else "Not available"
                ))
            all_passed = all(gt.passed for gt in gate_trace)
            return all_passed, gate_trace
