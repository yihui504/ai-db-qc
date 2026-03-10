"""Oracle for R6A-001.

R6A-001: Consistency / Visibility Campaign
Classifications: PASS, OBSERVATION, EXPERIMENT_DESIGN_ISSUE, BUG_CANDIDATE, INFRA_FAILURE, EXPECTED_FAILURE

Round 1 Core: CONS-001, CONS-002, CONS-003, CONS-005
Round 2 Extended: CONS-004, CONS-006
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
        insert_step = self._extract_step_result(trace, "insert")
        if not insert_step or insert_step.get("result_status") != "success":
            return {
                "classification": "EXPERIMENT_DESIGN_ISSUE",
                "satisfied": False,
                "reasoning": "Insert operation failed or missing"
            }

        insert_count = insert_step.get("insert_count", 0)
        expected_count = expectations.get("insert_count_immediate", 5)

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
            "reasoning": f"insert() returns {insert_count} immediately. Pre-flush num_entities={pre_count}, post-flush={post_count}.",
            "evidence": {
                "insert_count": insert_count,
                "num_entities_pre_flush": pre_count,
                "num_entities_post_flush": post_count,
                "flush_enables_storage_visibility": post_count == expected_count
            },
            "interpretation": "Flush enables storage_count visibility. Pre-flush behavior is documented."
        }

    def _eval_cons002(self, result: Dict, trace: list, expectations: Dict) -> Dict:
        """Evaluate CONS-002: Storage-Visible vs Search-Visible Relationship"""
        storage_check = self._extract_step_result(trace, "check_storage_count")
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
        search_without_status = search_without.get("result_status", "unknown")
        search_with_count = len(search_with.get("result", {}).get("results", []))

        # Document two-stage visibility
        return {
            "classification": "OBSERVATION",
            "satisfied": True,
            "reasoning": f"Storage-visible after flush: count={storage_count}. Search without load: {search_without_status} (count={search_without_count}). Search with load: count={search_with_count}.",
            "evidence": {
                "storage_count_post_flush": storage_count,
                "search_without_load_status": search_without_status,
                "search_without_load_count": search_without_count,
                "search_with_load_count": search_with_count,
                "two_stage_visibility": True
            },
            "interpretation": "Flush enables storage-visible. Search requires load (separate concern from flush)."
        }

    def _eval_cons003(self, result: Dict, trace: list, expectations: Dict) -> Dict:
        """Evaluate CONS-003: Load/Release/Reload Gate"""
        search_unloaded = self._extract_step_result(trace, "search_unloaded")
        search_after_reload = self._extract_step_result(trace, "search_after_reload")
        baseline = self._extract_step_result(trace, "search_baseline")

        if not search_unloaded or not search_after_reload or not baseline:
            return {
                "classification": "EXPERIMENT_DESIGN_ISSUE",
                "satisfied": False,
                "reasoning": "Missing required steps"
            }

        unloaded_status = search_unloaded.get("result_status", "unknown")
        unloaded_error = search_unloaded.get("error", "")
        baseline_count = len(baseline.get("result", {}).get("results", []))
        reload_count = len(search_after_reload.get("result", {}).get("results", []))

        # STRICT gate: unloaded search should fail
        if unloaded_status == "success":
            return {
                "classification": "BUG_CANDIDATE",
                "satisfied": False,
                "reasoning": f"Search succeeded on unloaded collection. Load gate NOT enforced.",
                "evidence": {
                    "search_unloaded_status": "success",
                    "expected": "EXPECTED_FAILURE or error"
                }
            }

        # Check reload restored search
        if reload_count != baseline_count:
            return {
                "classification": "BUG_CANDIDATE",
                "satisfied": False,
                "reasoning": f"Reload search count mismatch: baseline={baseline_count}, reload={reload_count}",
                "evidence": {
                    "baseline_count": baseline_count,
                    "reload_count": reload_count
                }
            }

        return {
            "classification": "PASS",
            "satisfied": True,
            "reasoning": f"Load gate enforced (unloaded: {unloaded_status}). Reload restored search (count={reload_count}).",
            "evidence": {
                "search_unloaded_status": unloaded_status,
                "search_unloaded_error": unloaded_error if unloaded_status == "error" else None,
                "baseline_count": baseline_count,
                "reload_count": reload_count,
                "load_gate_enforced": True,
                "reload_restores": True
            }
        }

    def _eval_cons004(self, result: Dict, trace: list, expectations: Dict) -> Dict:
        """Evaluate CONS-004: Insert-Search Timing Window Observation (Round 2)"""
        search_t0 = self._extract_step_result(trace, "search_t0_immediate")
        search_t1 = self._extract_step_result(trace, "search_t1_after_wait")
        search_after_flush = self._extract_step_result(trace, "search_after_flush_baseline")

        if not search_t0 or not search_t1 or not search_after_flush:
            return {
                "classification": "EXPERIMENT_DESIGN_ISSUE",
                "satisfied": False,
                "reasoning": "Missing required timing steps"
            }

        t0_count = len(search_t0.get("result", {}).get("results", []))
        t1_count = len(search_t1.get("result", {}).get("results", []))
        flush_count = len(search_after_flush.get("result", {}).get("results", []))

        # OBSERVATION - document without strong conclusions
        return {
            "classification": "OBSERVATION",
            "satisfied": True,
            "reasoning": f"Observed insert-search visibility within tested wait window. t=0: {t0_count}, t=1s: {t1_count}, after flush: {flush_count}.",
            "evidence": {
                "search_t0_count": t0_count,
                "search_t1_count": t1_count,
                "search_after_flush_count": flush_count,
                "wait_window_tested": "1 second"
            },
            "interpretation": "Observed behavior documented. No strong conclusion预设 about timing requirements.",
            "note": "Default classification: OBSERVATION. Could be EXPERIMENT_DESIGN_ISSUE if test setup invalid."
        }

    def _eval_cons005(self, result: Dict, trace: list, expectations: Dict) -> Dict:
        """Evaluate CONS-005: Release Preserves Storage Data"""
        baseline_count_step = self._extract_step_result(trace, "record_storage_count_baseline")
        after_release = self._extract_step_result(trace, "check_storage_count_after_release")
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
                "reasoning": f"Storage count changed after release: baseline={baseline_count}, after release={release_count}",
                "evidence": {
                    "baseline_count": baseline_count,
                    "release_count": release_count,
                    "data_loss": True
                }
            }

        if baseline_results_count != reload_count:
            return {
                "classification": "BUG_CANDIDATE",
                "satisfied": False,
                "reasoning": f"Reload search count mismatch: baseline={baseline_results_count}, reload={reload_count}",
                "evidence": {
                    "baseline_count": baseline_results_count,
                    "reload_count": reload_count
                }
            }

        return {
            "classification": "PASS",
            "satisfied": True,
            "reasoning": f"Release preserves storage (count={release_count}). Reload restores search (count={reload_count}).",
            "evidence": {
                "storage_preserved": baseline_count == release_count,
                "search_restored": baseline_results_count == reload_count,
                "baseline_count": baseline_count,
                "release_count": release_count,
                "baseline_results": baseline_results_count,
                "reload_results": reload_count
            }
        }

    def _eval_cons006(self, result: Dict, trace: list, expectations: Dict) -> Dict:
        """Evaluate CONS-006: Repeated Flush Stability (Round 2)"""
        before_storage = self._extract_step_result(trace, "check_storage_state_before_second")
        after_storage = self._extract_step_result(trace, "check_storage_state_after_second")
        before_search = self._extract_step_result(trace, "check_search_state_before_second")
        after_search = self._extract_step_result(trace, "check_search_state_after_second")

        if not before_storage or not after_storage:
            return {
                "classification": "EXPERIMENT_DESIGN_ISSUE",
                "satisfied": False,
                "reasoning": "Missing storage state checks"
            }

        before_storage_count = before_storage.get("num_entities", -1)
        after_storage_count = after_storage.get("num_entities", -1)

        # Check for contradictory regressions in storage
        storage_regression = False
        if before_storage_count != after_storage_count:
            storage_regression = True

        # Check search states (if available)
        search_regression = False
        before_search_count = None
        after_search_count = None

        if before_search and after_search:
            before_search_count = len(before_search.get("result", {}).get("results", []))
            after_search_count = len(after_search.get("result", {}).get("results", []))
            if before_search_count != after_search_count:
                search_regression = True

        # OBSERVATION - document stability
        classification = "OBSERVATION"
        reasoning = f"Repeated flush: storage before={before_storage_count}, after={after_storage_count}"
        if before_search_count is not None:
            reasoning += f". Search before={before_search_count}, after={after_search_count}"

        if storage_regression or search_regression:
            classification = "BUG_CANDIDATE"
            reasoning += ". Contradictory regression detected!"

        return {
            "classification": classification,
            "satisfied": not (storage_regression or search_regression),
            "reasoning": reasoning,
            "evidence": {
                "storage_before": before_storage_count,
                "storage_after": after_storage_count,
                "storage_regression": storage_regression,
                "search_before": before_search_count,
                "search_after": after_search_count,
                "search_regression": search_regression
            },
            "interpretation": "Repeated flush should not introduce contradictory visibility regressions.",
            "note": "Minimal evidence: storage/search state before/after second flush."
        }
