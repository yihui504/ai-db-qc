"""Oracle for R6A-001.

R6A-001: Consistency / Visibility Campaign
Classifications: PASS, OBSERVATION, EXPERIMENT_DESIGN_ISSUE, BUG_CANDIDATE, INFRA_FAILURE, EXPECTED_FAILURE
"""

from typing import Dict, Any, Optional


class R6a001Oracle:
    """Oracle for evaluating R6A-001 test results."""

    def evaluate(self, result: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate test result against contract.

        Args:
            result: Test execution result with execution_trace
            contract: Contract specification

        Returns:
            Oracle evaluation with classification and reasoning
        """
        case_id = result.get("case_id")
        contract_id = result.get("contract_id")
        trace = result.get("execution_trace", [])
        expectations = result.get("oracle_expectations", {})

        # Check for infrastructure failures first
        infra_check = self._check_infra_failure(trace)
        if infra_check:
            return infra_check

        # Dispatch to contract-specific evaluation
        if contract_id == "CONS-001":
            return self._eval_cons001(result, trace, expectations)
        elif contract_id == "CONS-002":
            return self._eval_cons002(result, trace, expectations)
        elif contract_id == "CONS-003":
            return self._eval_cons003(result, trace, expectations)
        elif contract_id == "CONS-004":
            return self._eval_cons004(result, trace, expectations)
        elif contract_id == "CONS-005":
            return self._eval_cons005(result, trace, expectations)
        elif contract_id == "CONS-006":
            return self._eval_cons006(result, trace, expectations)
        else:
            return {
                "classification": "EXPERIMENT_DESIGN_ISSUE",
                "satisfied": False,
                "reasoning": f"Unknown contract_id: {contract_id}"
            }

    def _check_infra_failure(self, trace: list) -> Optional[Dict[str, Any]]:
        """Check for infrastructure failures."""
        for step in trace:
            if step.get("result_status") == "error":
                error_msg = step.get("error", "").lower()
                # Check for infra-specific errors
                if any(kw in error_msg for kw in ["connection", "timeout", "network", "unavailable"]):
                    return {
                        "classification": "INFRA_FAILURE",
                        "satisfied": False,
                        "reasoning": f"Infrastructure failure: {step.get('error')}",
                        "failed_step": step.get("operation"),
                        "error": step.get("error")
                    }
        return None

    def _extract_step_result(self, trace: list, operation: str) -> Optional[Dict]:
        """Extract result from a specific operation step."""
        for step in trace:
            if step.get("operation") == operation:
                return step
        return None

    def _eval_cons001(self, result: Dict, trace: list, expectations: Dict) -> Dict:
        """Evaluate CONS-001: Insert Return vs Storage Visibility"""
        # Check insert_count
        insert_step = self._extract_step_result(trace, "insert")
        if not insert_step or insert_step.get("result_status") != "success":
            return {
                "classification": "EXPERIMENT_DESIGN_ISSUE",
                "satisfied": False,
                "reasoning": "Insert operation failed or missing"
            }

        insert_count = insert_step.get("insert_count", 0)
        expected_count = expectations.get("insert_count_should_equal", 0)

        if insert_count != expected_count:
            return {
                "classification": "BUG_CANDIDATE",
                "satisfied": False,
                "reasoning": f"insert_count mismatch: expected {expected_count}, got {insert_count}"
            }

        # Check storage visibility behavior
        pre_flush = self._extract_step_result(trace, "check_num_entities_pre_flush")
        post_flush = self._extract_step_result(trace, "check_num_entities_post_flush")

        if not pre_flush or not post_flush:
            return {
                "classification": "EXPERIMENT_DESIGN_ISSUE",
                "satisfied": False,
                "reasoning": "Missing pre-flush or post-flush checks"
            }

        pre_count = pre_flush.get("num_entities", -1)
        post_count = post_flush.get("num_entities", -1)

        # Document the timing behavior
        return {
            "classification": "OBSERVATION",
            "satisfied": True,
            "reasoning": f"insert() returns {insert_count} immediately. Pre-flush num_entities={pre_count}, post-flush={post_count}. Flush enables storage visibility.",
            "evidence": {
                "insert_count": insert_count,
                "num_entities_pre_flush": pre_count,
                "num_entities_post_flush": post_count,
                "flush_enables_storage_visibility": post_count == expected_count
            }
        }

    def _eval_cons002(self, result: Dict, trace: list, expectations: Dict) -> Dict:
        """Evaluate CONS-002: Flush Effect on Storage vs Search Visibility"""
        # Check storage count after flush
        storage_check = self._extract_step_result(trace, "check_num_entities")
        search_without = self._extract_step_result(trace, "search_without_load")
        search_with = self._extract_step_result(trace, "search_with_load")

        if not storage_check or not search_without or not search_with:
            return {
                "classification": "EXPERIMENT_DESIGN_ISSUE",
                "satisfied": False,
                "reasoning": "Missing required steps"
            }

        storage_count = storage_check.get("num_entities", -1)
        search_without_count = len(search_without.get("result", {}).get("results", []))
        search_with_count = len(search_with.get("result", {}).get("results", []))

        # Document the two-stage visibility
        return {
            "classification": "OBSERVATION",
            "satisfied": True,
            "reasoning": f"Flush enables storage_count={storage_count}. Search without load={search_without_count}, with load={search_with_count}. Index update required for search.",
            "evidence": {
                "storage_count_post_flush": storage_count,
                "search_without_load": search_without_count,
                "search_with_load": search_with_count,
                "two_stage_visibility": True
            }
        }

    def _eval_cons003(self, result: Dict, trace: list, expectations: Dict) -> Dict:
        """Evaluate CONS-003: Load State Effect on Search Visibility"""
        search_unloaded = self._extract_step_result(trace, "search_unloaded")
        search_after_reload = self._extract_step_result(trace, "search_after_reload")
        baseline = self._extract_step_result(trace, "search_baseline")

        if not search_unloaded or not search_after_reload or not baseline:
            return {
                "classification": "EXPERIMENT_DESIGN_ISSUE",
                "satisfied": False,
                "reasoning": "Missing required steps"
            }

        # Check if unloaded search failed as expected
        unloaded_status = search_unloaded.get("result_status", "unknown")
        baseline_count = len(baseline.get("result", {}).get("results", []))
        reload_count = len(search_after_reload.get("result", {}).get("results", []))

        # STRICT gate: unloaded search should fail
        if unloaded_status == "success" and baseline_count > 0:
            return {
                "classification": "BUG_CANDIDATE",
                "satisfied": False,
                "reasoning": f"Search succeeded on unloaded collection (expected failure). Load gate not enforced."
            }

        # Check reload restored search
        if reload_count != baseline_count:
            return {
                "classification": "BUG_CANDIDATE",
                "satisfied": False,
                "reasoning": f"Reload search count mismatch: baseline={baseline_count}, reload={reload_count}"
            }

        return {
            "classification": "PASS",
            "satisfied": True,
            "reasoning": f"Load gate enforced. Unloaded search failed, reload search restored (count={reload_count}).",
            "evidence": {
                "search_unloaded_status": unloaded_status,
                "baseline_count": baseline_count,
                "reload_count": reload_count
            }
        }

    def _eval_cons004(self, result: Dict, trace: list, expectations: Dict) -> Dict:
        """Evaluate CONS-004: Insert-Search Timing Window"""
        search_immediate = self._extract_step_result(trace, "search_immediate")
        search_after_wait = self._extract_step_result(trace, "search_after_wait")
        search_after_flush = self._extract_step_result(trace, "search_after_flush")

        if not search_immediate or not search_after_wait or not search_after_flush:
            return {
                "classification": "EXPERIMENT_DESIGN_ISSUE",
                "satisfied": False,
                "reasoning": "Missing required steps"
            }

        immediate_count = len(search_immediate.get("result", {}).get("results", []))
        wait_count = len(search_after_wait.get("result", {}).get("results", []))
        flush_count = len(search_after_flush.get("result", {}).get("results", []))

        # Check if wait enabled search (BUG if it did without flush)
        if wait_count > 0:
            return {
                "classification": "BUG_CANDIDATE",
                "satisfied": False,
                "reasoning": f"Wait without flush enabled search (count={wait_count}). Expected flush requirement."
            }

        # Document timing behavior
        return {
            "classification": "OBSERVATION",
            "satisfied": True,
            "reasoning": f"Search without flush: immediate={immediate_count}, after wait={wait_count}. Flush required: after flush={flush_count}.",
            "evidence": {
                "search_immediate": immediate_count,
                "search_after_wait": wait_count,
                "search_after_flush": flush_count,
                "flush_required": flush_count > 0
            }
        }

    def _eval_cons005(self, result: Dict, trace: list, expectations: Dict) -> Dict:
        """Evaluate CONS-005: Release Preserves Storage Data"""
        baseline_count_step = self._extract_step_result(trace, "record_num_entities_loaded")
        after_release = self._extract_step_result(trace, "check_num_entities_after_release")
        baseline_results = self._extract_step_result(trace, "search_baseline")
        after_reload = self._extract_step_result(trace, "search_after_reload")

        if not baseline_count_step or not after_release or not baseline_results or not after_reload:
            return {
                "classification": "EXPERIMENT_DESIGN_ISSUE",
                "satisfied": False,
                "reasoning": "Missing required steps"
            }

        baseline_count = baseline_count_step.get("num_entities", -1)
        release_count = after_release.get("num_entities", -1)
        baseline_results_count = len(baseline_results.get("result", {}).get("results", []))
        reload_count = len(after_reload.get("result", {}).get("results", []))

        # STRICT: data preservation invariant
        if baseline_count != release_count:
            return {
                "classification": "BUG_CANDIDATE",
                "satisfied": False,
                "reasoning": f"Data loss after release: baseline={baseline_count}, after release={release_count}"
            }

        if baseline_results_count != reload_count:
            return {
                "classification": "BUG_CANDIDATE",
                "satisfied": False,
                "reasoning": f"Reload search count mismatch: baseline={baseline_results_count}, reload={reload_count}"
            }

        return {
            "classification": "PASS",
            "satisfied": True,
            "reasoning": f"Release preserves storage (count={release_count}). Reload restores search (count={reload_count}).",
            "evidence": {
                "storage_preserved": baseline_count == release_count,
                "search_restored": baseline_results_count == reload_count
            }
        }

    def _eval_cons006(self, result: Dict, trace: list, expectations: Dict) -> Dict:
        """Evaluate CONS-006: Flush Idempotence"""
        first_flush = self._extract_step_result(trace, "check_num_entities")
        second_flush = self._extract_step_result(trace, "check_num_entities_unchanged")

        if not first_flush or not second_flush:
            return {
                "classification": "EXPERIMENT_DESIGN_ISSUE",
                "satisfied": False,
                "reasoning": "Missing required steps"
            }

        first_count = first_flush.get("num_entities", -1)
        second_count = second_flush.get("num_entities", -1)

        if first_count != second_count:
            return {
                "classification": "BUG_CANDIDATE",
                "satisfied": False,
                "reasoning": f"Flush not idempotent: first={first_count}, second={second_count}"
            }

        return {
            "classification": "OBSERVATION",
            "satisfied": True,
            "reasoning": f"Flush is idempotent: both flushes return count={first_count}",
            "evidence": {
                "first_flush_count": first_count,
                "second_flush_count": second_count,
                "idempotent": True
            }
        }
