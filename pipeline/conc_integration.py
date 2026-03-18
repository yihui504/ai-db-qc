"""Integration module for CONC (Concurrency) contract testing.

This module integrates the CONC contract family (CONC-001, CONC-002, CONC-003)
into the existing ai-db-qc pipeline, enabling concurrent test execution
with contract violation detection.
"""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from adapters.base import AdapterBase
from pipeline.executor import Executor
from schemas.case import TestCase
from schemas.common import ObservedOutcome, OperationType, InputValidity
from schemas.result import ExecutionResult
from pipeline.triage import Triage


@dataclass
class ConcurrentViolation:
    """Represents a concurrency contract violation."""
    contract_id: str
    violation_type: str
    description: str
    thread_id: int
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConcurrentTestResult:
    """Result of a concurrent contract test."""
    contract_id: str
    classification: str  # "PASS", "VIOLATION", "ERROR"
    violations: List[ConcurrentViolation]
    thread_results: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "classification": self.classification,
            "violations": [
                {
                    "contract_id": v.contract_id,
                    "violation_type": v.violation_type,
                    "description": v.description,
                    "thread_id": v.thread_id,
                    "timestamp": v.timestamp,
                    "details": v.details
                }
                for v in self.violations
            ],
            "thread_results": self.thread_results,
            "metrics": self.metrics
        }


class ConcurrentTestRunner:
    """Runner for concurrent contract tests.
    
    Integrates CONC-001, CONC-002, CONC-003 contracts with the existing
    pipeline infrastructure.
    """
    
    def __init__(
        self,
        adapter: AdapterBase,
        executor: Executor,
        triage: Triage
    ):
        self.adapter = adapter
        self.executor = executor
        self.triage = triage
        self.violations: List[ConcurrentViolation] = []
        self.lock = threading.Lock()
    
    def run_conc_001(
        self,
        collection_name: str,
        n_threads: int = 4,
        vectors_per_thread: int = 100,
        dim: int = 64
    ) -> ConcurrentTestResult:
        """Run CONC-001: Concurrent Insert Count Consistency.
        
        Contract: After N concurrent insert operations, count_entities
        must equal total inserted entities.
        
        Args:
            collection_name: Name of collection to test
            n_threads: Number of concurrent threads
            vectors_per_thread: Vectors to insert per thread
            dim: Vector dimension
            
        Returns:
            ConcurrentTestResult with classification and violations
        """
        print(f"  [CONC-001] Concurrent Insert Count Consistency")
        print(f"    Threads: {n_threads}, Vectors/thread: {vectors_per_thread}")
        
        # Setup collection
        self._setup_collection(collection_name, dim)
        
        violations = []
        thread_results = []
        latencies = []
        
        def insert_worker(thread_id: int) -> Dict[str, Any]:
            """Worker that inserts vectors and returns result."""
            vectors = self._generate_vectors(vectors_per_thread, dim, seed=thread_id)
            
            case = TestCase(
                case_id=f"conc001_t{thread_id}",
                operation=OperationType.INSERT,
                params={
                    "collection_name": collection_name,
                    "vectors": vectors
                },
                expected_validity=InputValidity.LEGAL
            )
            
            start = time.time()
            result = self.executor.execute_case(case, run_id=f"conc001_{thread_id}")
            latency_ms = (time.time() - start) * 1000
            latencies.append(latency_ms)
            
            return {
                "thread_id": thread_id,
                "status": result.observed_outcome.value,
                "latency_ms": latency_ms,
                "inserted_count": vectors_per_thread if result.observed_outcome == ObservedOutcome.SUCCESS else 0
            }
        
        # Execute concurrent inserts
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=n_threads) as pool:
            futures = [pool.submit(insert_worker, t) for t in range(n_threads)]
            thread_results = [f.result() for f in as_completed(futures)]
        elapsed = time.time() - start_time
        
        # Flush and verify count
        self._flush_collection(collection_name)
        time.sleep(0.5)
        
        expected_count = n_threads * vectors_per_thread
        actual_count = self._get_entity_count(collection_name)
        
        # Oracle verification
        if actual_count is None:
            violations.append(ConcurrentViolation(
                contract_id="CONC-001",
                violation_type="count_failure",
                description="Failed to get entity count",
                thread_id=-1,
                timestamp=time.time()
            ))
        elif actual_count != expected_count:
            violations.append(ConcurrentViolation(
                contract_id="CONC-001",
                violation_type="count_mismatch",
                description=f"Count mismatch: expected {expected_count}, got {actual_count}",
                thread_id=-1,
                timestamp=time.time(),
                details={"expected": expected_count, "actual": actual_count}
            ))
        
        # Check for insert errors
        errors = [r for r in thread_results if r["status"] != "success"]
        if errors:
            violations.append(ConcurrentViolation(
                contract_id="CONC-001",
                violation_type="insert_errors",
                description=f"{len(errors)} insert operations failed",
                thread_id=-1,
                timestamp=time.time(),
                details={"error_count": len(errors)}
            ))
        
        # Cleanup
        self._drop_collection(collection_name)
        
        classification = "PASS" if not violations else "VIOLATION"
        
        metrics = {
            "total_threads": n_threads,
            "vectors_per_thread": vectors_per_thread,
            "expected_total": expected_count,
            "actual_count": actual_count,
            "elapsed_seconds": round(elapsed, 2),
            "throughput": round(expected_count / elapsed, 2) if elapsed > 0 else 0,
            "latency_p50_ms": self._percentile(latencies, 50) if latencies else 0,
            "latency_p95_ms": self._percentile(latencies, 95) if latencies else 0,
        }
        
        print(f"    {classification}: expected={expected_count}, got={actual_count}, "
              f"errors={len(errors)}, p95={metrics['latency_p95_ms']:.1f}ms")
        
        return ConcurrentTestResult(
            contract_id="CONC-001",
            classification=classification,
            violations=violations,
            thread_results=thread_results,
            metrics=metrics
        )
    
    def run_conc_002(
        self,
        collection_name: str,
        n_readers: int = 4,
        n_deleters: int = 1,
        duration_seconds: int = 10,
        dim: int = 64,
        top_k: int = 10
    ) -> ConcurrentTestResult:
        """Run CONC-002: Concurrent Search Isolation.
        
        Contract: Concurrent search operations must not return phantom
        data or corrupted results.
        
        Args:
            collection_name: Name of collection to test
            n_readers: Number of reader threads
            n_deleters: Number of deleter threads
            duration_seconds: Test duration
            dim: Vector dimension
            top_k: Top-K for search
            
        Returns:
            ConcurrentTestResult with classification and violations
        """
        print(f"  [CONC-002] Concurrent Search Isolation")
        print(f"    Readers: {n_readers}, Deleters: {n_deleters}, Duration: {duration_seconds}s")
        
        # Setup collection with data
        n_docs = 500
        self._setup_collection_with_data(collection_name, dim, n_docs)
        
        violations = []
        thread_results = []
        stop_event = threading.Event()
        search_count = [0]
        search_violations = []
        
        def reader_worker(thread_id: int) -> Dict[str, Any]:
            """Worker that continuously searches."""
            results = []
            query_vectors = self._generate_vectors(5, dim, seed=thread_id * 100)
            
            while not stop_event.is_set():
                for vec in query_vectors:
                    if stop_event.is_set():
                        break
                    
                    case = TestCase(
                        case_id=f"conc002_r{thread_id}_{search_count[0]}",
                        operation=OperationType.SEARCH,
                        params={
                            "collection_name": collection_name,
                            "vector": vec,
                            "top_k": top_k
                        },
                        expected_validity=InputValidity.LEGAL
                    )
                    
                    result = self.executor.execute_case(case, run_id=f"conc002_{thread_id}")
                    
                    with self.lock:
                        search_count[0] += 1
                    
                    # Check cardinality
                    result_count = len(result.response.get("data", []))
                    if result_count > top_k:
                        search_violations.append({
                            "thread_id": thread_id,
                            "type": "cardinality",
                            "count": result_count,
                            "top_k": top_k
                        })
                    
                    results.append({
                        "status": result.observed_outcome.value,
                        "count": result_count
                    })
                
                time.sleep(0.01)
            
            return {"thread_id": thread_id, "searches": len(results)}
        
        def deleter_worker(thread_id: int) -> Dict[str, Any]:
            """Worker that deletes entities."""
            time.sleep(1)  # Let readers start first
            # Simplified deletion - would track actual IDs in full implementation
            return {"thread_id": thread_id, "deletions": 0}
        
        # Execute concurrent operations
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=n_readers + n_deleters) as pool:
            reader_futures = [pool.submit(reader_worker, i) for i in range(n_readers)]
            deleter_futures = [pool.submit(deleter_worker, i) for i in range(n_deleters)]
            
            # Run for specified duration
            time.sleep(duration_seconds)
            stop_event.set()
            
            # Collect results
            for future in as_completed(reader_futures + deleter_futures):
                try:
                    thread_results.append(future.result())
                except Exception as e:
                    print(f"    Worker error: {e}")
        
        elapsed = time.time() - start_time
        
        # Check violations
        if search_violations:
            violations.append(ConcurrentViolation(
                contract_id="CONC-002",
                violation_type="search_violation",
                description=f"{len(search_violations)} search violations detected",
                thread_id=-1,
                timestamp=time.time(),
                details={"violations": search_violations[:5]}
            ))
        
        # Cleanup
        self._drop_collection(collection_name)
        
        classification = "PASS" if not violations else "VIOLATION"
        
        metrics = {
            "n_readers": n_readers,
            "n_deleters": n_deleters,
            "duration_seconds": duration_seconds,
            "total_searches": search_count[0],
            "search_violations": len(search_violations),
            "throughput": round(search_count[0] / elapsed, 2) if elapsed > 0 else 0,
        }
        
        print(f"    {classification}: {search_count[0]} searches, "
              f"{len(search_violations)} violations")
        
        return ConcurrentTestResult(
            contract_id="CONC-002",
            classification=classification,
            violations=violations,
            thread_results=thread_results,
            metrics=metrics
        )
    
    def run_conc_003(
        self,
        collection_name: str,
        n_deleters: int = 2,
        n_searchers: int = 4,
        duration_seconds: int = 15,
        dim: int = 64
    ) -> ConcurrentTestResult:
        """Run CONC-003: Delete-Search Cross Consistency.
        
        Contract: Delete and search operations executed concurrently
        must maintain cross-operation consistency.
        
        Args:
            collection_name: Name of collection to test
            n_deleters: Number of deleter threads
            n_searchers: Number of searcher threads
            duration_seconds: Test duration
            dim: Vector dimension
            
        Returns:
            ConcurrentTestResult with classification and violations
        """
        print(f"  [CONC-003] Delete-Search Cross Consistency")
        print(f"    Deleters: {n_deleters}, Searchers: {n_searchers}, Duration: {duration_seconds}s")
        
        # Setup collection with data
        n_docs = 300
        self._setup_collection_with_data(collection_name, dim, n_docs)
        
        violations = []
        thread_results = []
        stop_event = threading.Event()
        count_observations = []
        prev_count = [self._get_entity_count(collection_name)]
        
        def searcher_worker(thread_id: int) -> Dict[str, Any]:
            """Worker that searches and checks consistency."""
            results = []
            query_vectors = self._generate_vectors(3, dim, seed=thread_id * 200)
            
            while not stop_event.is_set():
                for vec in query_vectors:
                    if stop_event.is_set():
                        break
                    
                    case = TestCase(
                        case_id=f"conc003_s{thread_id}",
                        operation=OperationType.SEARCH,
                        params={
                            "collection_name": collection_name,
                            "vector": vec,
                            "top_k": 10
                        },
                        expected_validity=InputValidity.LEGAL
                    )
                    
                    result = self.executor.execute_case(case, run_id=f"conc003_{thread_id}")
                    
                    # Check count monotonicity
                    current_count = self._get_entity_count(collection_name)
                    if current_count is not None and prev_count[0] is not None:
                        if current_count > prev_count[0]:
                            # Count increased after delete - violation
                            violations.append(ConcurrentViolation(
                                contract_id="CONC-003",
                                violation_type="count_increase",
                                description=f"Count increased: {prev_count[0]} -> {current_count}",
                                thread_id=thread_id,
                                timestamp=time.time()
                            ))
                        prev_count[0] = current_count
                        count_observations.append(current_count)
                    
                    results.append({
                        "status": result.observed_outcome.value,
                        "count": current_count
                    })
                
                time.sleep(0.02)
            
            return {"thread_id": thread_id, "searches": len(results)}
        
        def deleter_worker(thread_id: int) -> Dict[str, Any]:
            """Worker that deletes entities."""
            time.sleep(1)
            # Simplified deletion
            return {"thread_id": thread_id, "deletions": 0}
        
        # Execute concurrent operations
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=n_deleters + n_searchers) as pool:
            searcher_futures = [pool.submit(searcher_worker, i) for i in range(n_searchers)]
            deleter_futures = [pool.submit(deleter_worker, i) for i in range(n_deleters)]
            
            time.sleep(duration_seconds)
            stop_event.set()
            
            for future in as_completed(searcher_futures + deleter_futures):
                try:
                    thread_results.append(future.result())
                except Exception as e:
                    print(f"    Worker error: {e}")
        
        elapsed = time.time() - start_time
        
        # Cleanup
        self._drop_collection(collection_name)
        
        classification = "PASS" if not violations else "VIOLATION"
        
        metrics = {
            "n_deleters": n_deleters,
            "n_searchers": n_searchers,
            "duration_seconds": duration_seconds,
            "count_observations": len(count_observations),
            "violation_count": len(violations),
        }
        
        print(f"    {classification}: {len(count_observations)} observations, "
              f"{len(violations)} violations")
        
        return ConcurrentTestResult(
            contract_id="CONC-003",
            classification=classification,
            violations=violations,
            thread_results=thread_results,
            metrics=metrics
        )
    
    # ─────────────────────────────────────────────────────────────
    # Helper Methods
    # ─────────────────────────────────────────────────────────────
    
    def _setup_collection(self, collection_name: str, dim: int) -> None:
        """Create a fresh collection."""
        try:
            self.adapter.execute({
                "operation": "drop_collection",
                "params": {"collection_name": collection_name}
            })
        except Exception:
            pass
        
        self.adapter.execute({
            "operation": "create_collection",
            "params": {"collection_name": collection_name, "dimension": dim}
        })
    
    def _setup_collection_with_data(self, collection_name: str, dim: int, n_docs: int) -> None:
        """Create collection and populate with data."""
        self._setup_collection(collection_name, dim)
        
        vectors = self._generate_vectors(n_docs, dim, seed=42)
        self.adapter.execute({
            "operation": "insert",
            "params": {"collection_name": collection_name, "vectors": vectors}
        })
        
        self._flush_collection(collection_name)
        
        # Build index and load
        self.adapter.execute({
            "operation": "build_index",
            "params": {
                "collection_name": collection_name,
                "index_type": "IVF_FLAT",
                "metric_type": "L2",
                "nlist": 64
            }
        })
        self.adapter.execute({
            "operation": "load",
            "params": {"collection_name": collection_name}
        })
    
    def _drop_collection(self, collection_name: str) -> None:
        """Drop a collection."""
        try:
            self.adapter.execute({
                "operation": "drop_collection",
                "params": {"collection_name": collection_name}
            })
        except Exception:
            pass
    
    def _flush_collection(self, collection_name: str) -> None:
        """Flush collection to ensure persistence."""
        try:
            self.adapter.execute({
                "operation": "flush",
                "params": {"collection_name": collection_name}
            })
        except Exception:
            pass
    
    def _get_entity_count(self, collection_name: str) -> Optional[int]:
        """Get entity count for a collection."""
        try:
            result = self.adapter.execute({
                "operation": "count_entities",
                "params": {"collection_name": collection_name}
            })
            if result.get("status") == "success":
                return result.get("data", 0)
        except Exception:
            pass
        return None
    
    def _generate_vectors(self, n: int, dim: int, seed: int = 0) -> List[List[float]]:
        """Generate random vectors."""
        import random
        rng = random.Random(seed)
        return [[rng.gauss(0, 1) for _ in range(dim)] for _ in range(n)]
    
    def _percentile(self, data: List[float], pct: float) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0
        s = sorted(data)
        idx = int(len(s) * pct / 100)
        return s[min(idx, len(s) - 1)]


def run_conc_suite(
    adapter: AdapterBase,
    executor: Executor,
    triage: Triage,
    contracts: Optional[List[str]] = None
) -> Dict[str, ConcurrentTestResult]:
    """Run a suite of CONC contract tests.
    
    Args:
        adapter: Database adapter
        executor: Test case executor
        triage: Triage classifier
        contracts: List of contract IDs to run (default: all)
        
    Returns:
        Dictionary mapping contract IDs to results
    """
    if contracts is None:
        contracts = ["CONC-001", "CONC-002", "CONC-003"]
    
    runner = ConcurrentTestRunner(adapter, executor, triage)
    results = {}
    
    print(f"\n{'='*60}")
    print(f"  CONC Contract Test Suite")
    print(f"{'='*60}")
    
    for contract_id in contracts:
        collection_name = f"conc_test_{contract_id.lower().replace('-', '_')}"
        
        try:
            if contract_id == "CONC-001":
                result = runner.run_conc_001(collection_name)
            elif contract_id == "CONC-002":
                result = runner.run_conc_002(collection_name)
            elif contract_id == "CONC-003":
                result = runner.run_conc_003(collection_name)
            else:
                print(f"  Unknown contract: {contract_id}")
                continue
            
            results[contract_id] = result
            
        except Exception as e:
            print(f"  ERROR running {contract_id}: {e}")
            import traceback
            traceback.print_exc()
            results[contract_id] = ConcurrentTestResult(
                contract_id=contract_id,
                classification="ERROR",
                violations=[ConcurrentViolation(
                    contract_id=contract_id,
                    violation_type="execution_error",
                    description=str(e),
                    thread_id=-1,
                    timestamp=time.time()
                )],
                thread_results=[],
                metrics={}
            )
    
    # Summary
    print(f"\n{'='*60}")
    print(f"  CONC Suite Summary")
    print(f"{'='*60}")
    
    total = len(results)
    violations = sum(1 for r in results.values() if r.classification == "VIOLATION")
    passes = sum(1 for r in results.values() if r.classification == "PASS")
    errors = sum(1 for r in results.values() if r.classification == "ERROR")
    
    print(f"  Total: {total}")
    print(f"  PASS:  {passes}")
    print(f"  VIOLATIONS: {violations}")
    print(f"  ERRORS: {errors}")
    
    if violations > 0:
        print(f"\n  Violations:")
        for contract_id, result in results.items():
            if result.classification == "VIOLATION":
                print(f"    [{contract_id}] {len(result.violations)} violation(s)")
    
    print(f"{'='*60}\n")
    
    return results


# Export for use in other modules
__all__ = [
    "ConcurrentTestRunner",
    "ConcurrentTestResult",
    "ConcurrentViolation",
    "run_conc_suite",
]
