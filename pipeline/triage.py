"""Triage classification."""

from __future__ import annotations

from schemas.case import TestCase
from schemas.common import BugType, InputValidity, ObservedOutcome
from schemas.result import ExecutionResult
from schemas.triage import TriageResult


class Triage:
    """Classify ExecutionResult into bug types."""

    def classify(self, case: TestCase, result: ExecutionResult, naive: bool = False) -> TriageResult | None:
        """
        Classify using case + result.

        Uses case.expected_validity (not passed as separate param).
        Enforces red-line: Type-3/4 require precondition_pass=true.
        Returns TriageResult or None if not a bug.

        Args:
            case: Test case with expected validity
            result: Execution result with observed outcome
            naive: If True, classify all illegal-fail as Type-2 without diagnostic check.
                   If False (default), use diagnostic-aware classification.
        """
        input_validity = case.expected_validity

        # Step 1: Check precondition red-line
        if not result.precondition_pass:
            if input_validity == InputValidity.ILLEGAL:
                return TriageResult(
                    case_id=case.case_id,
                    run_id=result.run_id,
                    final_type=BugType.TYPE_2,
                    input_validity=input_validity.value,
                    observed_outcome=result.observed_outcome.value,
                    precondition_pass=False,
                    rationale="Illegal input with poor diagnostic"
                )
            else:
                return TriageResult(
                    case_id=case.case_id,
                    run_id=result.run_id,
                    final_type=BugType.TYPE_2_PRECONDITION_FAILED,
                    input_validity=input_validity.value,
                    observed_outcome=result.observed_outcome.value,
                    precondition_pass=False,
                    rationale="Contract-valid but precondition-fail"
                )

        # Step 2: Check input validity
        if input_validity == InputValidity.ILLEGAL:
            if result.observed_success:
                return TriageResult(
                    case_id=case.case_id,
                    run_id=result.run_id,
                    final_type=BugType.TYPE_1,
                    input_validity=input_validity.value,
                    observed_outcome=result.observed_outcome.value,
                    precondition_pass=True,
                    rationale="Illegal operation succeeded"
                )
            else:
                # Illegal case failed
                if naive:
                    # Naive mode: all illegal-fail are Type-2, no diagnostic check
                    return TriageResult(
                        case_id=case.case_id,
                        run_id=result.run_id,
                        final_type=BugType.TYPE_2,
                        input_validity=input_validity.value,
                        observed_outcome=result.observed_outcome.value,
                        precondition_pass=True,
                        rationale="Illegal case failed (naive classification)"
                    )
                else:
                    # Diagnostic-aware mode: check if error has sufficient diagnostics
                    # Type-2 only if error is NOT sufficiently diagnostic
                    if self._has_good_diagnostics(result):
                        # Error has good diagnostics - not a bug
                        return None
                    else:
                        # Poor diagnostics - Type-2
                        return TriageResult(
                            case_id=case.case_id,
                            run_id=result.run_id,
                            final_type=BugType.TYPE_2,
                            input_validity=input_validity.value,
                            observed_outcome=result.observed_outcome.value,
                            precondition_pass=True,
                            rationale="Illegal operation with poor diagnostic"
                        )

        # Step 3: Legal input, precondition passed
        if not result.observed_success:
            return TriageResult(
                case_id=case.case_id,
                run_id=result.run_id,
                final_type=BugType.TYPE_3,
                input_validity=input_validity.value,
                observed_outcome=result.observed_outcome.value,
                precondition_pass=True,
                rationale="Legal operation failed (precondition satisfied)"
            )

        # Step 4: Legal input, precondition passed, succeeded
        # Phase 3: Check for actual oracle failures
        if result.oracle_results and any(not o.passed for o in result.oracle_results):
            # Collect which oracles failed
            failed_oracles = [o for o in result.oracle_results if not o.passed]
            oracle_names = ", ".join(o.oracle_id for o in failed_oracles)
            return TriageResult(
                case_id=case.case_id,
                run_id=result.run_id,
                final_type=BugType.TYPE_4,
                input_validity=input_validity.value,
                observed_outcome=result.observed_outcome.value,
                precondition_pass=True,
                rationale=f"Semantic violation: {oracle_names}"
            )

        # Not a bug
        return None

    def _has_good_diagnostics(self, result: ExecutionResult) -> bool:
        """
        Check if error response has sufficient diagnostic information.

        Returns True if error message has good diagnostics (specific parameter names,
        clear issue descriptions, actionable guidance), False if diagnostics are poor.

        Enhanced for experimental strengthening - better distinguishes
        good diagnostics (mentioning specific parameters, values, or solutions)
        from poor diagnostics (generic errors, vague complaints).
        """
        if result.observed_outcome == ObservedOutcome.SUCCESS:
            return True  # No error, so "diagnostics" are fine

        if not result.error_message:
            return False  # No error message at all

        error_msg = result.error_message.lower()
        response = result.response or {}

        # Check for good diagnostic indicators
        # 1. Error has structured error_details with parameter name
        if "error_details" in response and "parameter" in response["error_details"]:
            return True  # Has parameter name in structured details

        # 2. Error message mentions specific parameter with value
        # Enhanced: Check for parameter names WITH context
        param_contexts = [
            ("dimension", ["dimension", "size", "vector size", "number of dimensions"]),
            ("top_k", ["top_k", "top k", "top-k"]),
            ("metric_type", ["metric_type", "metric type", "distance metric"]),
            ("collection_name", ["collection", "table"]),
            ("vectors", ["vector", "embedding"]),
            ("filter", ["filter", "expression"])
        ]

        for param_name, param_aliases in param_contexts:
            for alias in param_aliases:
                if alias in error_msg:
                    # Additional check: Is it actionable?
                    # Good: "dimension must be 128" or "invalid dimension: -1"
                    # Poor: "dimension error" (too vague)
                    if any(actionable in error_msg for actionable in
                           ["must be", "should be", "expected", "invalid value", "cannot", "must not"]):
                        return True  # Specific parameter + actionable guidance

        # 3. Error message provides clear next steps
        helpful_phrases = [
            "try using", "instead of", "ensure that", "make sure",
            "please check", "verify that", "confirm that"
        ]
        if any(phrase in error_msg for phrase in helpful_phrases):
            return True  # Provides actionable guidance

        # 4. Error message is clearly poor diagnostics
        # Poor: Very generic messages without any specific information
        poor_indicators = [
            ("invalid parameter", "parameter" not in error_msg or
             any(param in error_msg for param in [p for params in param_contexts for p in params])),
            ("operation failed", not any(symptom in error_msg for symptom in
             ["timeout", "connection", "network", "permission"])),
            ("error occurred", True)  # Always poor
        ]

        for poor_phrase, is_poor in poor_indicators:
            if poor_phrase in error_msg and is_poor:
                return False

        # 5. Error message mentions specific exception types (can be good)
        # Good: "DimensionMismatchException", "InvalidTopKException"
        # Poor: "InternalError", "RuntimeException"
        exception_type = None
        if "exception" in error_msg.lower():
            # Try to extract exception type
            for word in error_msg.split():
                if "exception" in word.lower():
                    exception_type = word.strip(" ,.)(;")
                    break

        if exception_type:
            # Generic exceptions are poor
            generic_exceptions = ["runtime", "internal", "system", "unknown"]
            if any(gen in exception_type.lower() for gen in generic_exceptions):
                return False
            # Specific exceptions are good
            return True

        # Default: moderately conservative
        # If error mentions any technical term, give it benefit of doubt
        technical_terms = ["collection", "index", "dimension", "metric", "vector", "search"]
        if any(term in error_msg for term in technical_terms):
            return True

        return False  # Default to poor diagnostics
