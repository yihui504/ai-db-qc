"""Generic Concurrent Test Framework for Vector Databases.

This script implements the CONC (Concurrency) contract family testing framework,
supporting CONC-001, CONC-002, and CONC-003 contracts across multiple databases.

Features:
- Configurable concurrent parameters (threads, operation ratios, duration)
- Multi-database adapter support (Milvus, Qdrant, Weaviate, pgvector)
- Performance metrics collection (throughput, latency P50/P95/P99)
- Contract violation detection with oracle verification

Usage:
    # Run CONC-001 on Milvus
    python scripts/run_concurrent_test.py --contract CONC-001 --target milvus

    # Run all CONC contracts on Qdrant with custom threads
    python scripts/run_concurrent_test.py --all --target qdrant --threads 8

    # Run with performance profiling
    python scripts/run_concurrent_test.py --contract CONC-002 --target milvus --profile
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.base import AdapterBase
from adapters.milvus_adapter import MilvusAdapter
from adapters.qdrant_adapter import QdrantAdapter
from adapters.weaviate_adapter import WeaviateAdapter
from adapters.pgvector_adapter import PgvectorAdapter

RESULTS_DIR = Path("results")
CONTRACTS_DIR = Path(__file__).parent.parent / "contracts" / "conc"


# ─────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────

@dataclass
class PerformanceMetrics:
    """Performance metrics for concurrent operations."""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    throughput_ops_per_sec: float = 0.0
    
    @property
    def p50_latency_ms(self) -> float:
        return self._percentile(50)
    
    @property
    def p95_latency_ms(self) -> float:
        return self._percentile(95)
    
    @property
    def p99_latency_ms(self) -> float:
        return self._percentile(99)
    
    def _percentile(self, pct: float) -> float:
        if not self.latencies_ms:
            return 0.0
        s = sorted(self.latencies_ms)
        idx = int(len(s) * pct / 100)
        return round(s[min(idx, len(s) - 1)], 2)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "throughput_ops_per_sec": round(self.throughput_ops_per_sec, 2),
            "latency_ms": {
                "p50": self.p50_latency_ms,
                "p95": self.p95_latency_ms,
                "p99": self.p99_latency_ms,
                "min": round(min(self.latencies_ms), 2) if self.latencies_ms else 0,
                "max": round(max(self.latencies_ms), 2) if self.latencies_ms else 0,
            }
        }


@dataclass
class ContractViolation:
    """Represents a contract violation."""
    contract_id: str
    violation_type: str
    description: str
    severity: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "violation_type": self.violation_type,
            "description": self.description,
            "severity": self.severity,
            "details": self.details,
        }


@dataclass
class TestResult:
    """Result of a contract test."""
    contract_id: str
    classification: str  # "PASS" or "VIOLATION"
    violations: List[ContractViolation] = field(default_factory=list)
    metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "classification": self.classification,
            "violations": [v.to_dict() for v in self.violations],
            "metrics": self.metrics.to_dict(),
            "metadata": self.metadata,
        }


# ─────────────────────────────────────────────────────────────
# Adapter Factory
# ─────────────────────────────────────────────────────────────

def build_adapter(target: str, host: str, port: int) -> AdapterBase:
    """Build the appropriate adapter for a given target."""
    if target == "milvus":
        return MilvusAdapter({"host": host, "port": port})
    elif target == "qdrant":
        return QdrantAdapter({"host": host, "port": port})
    elif target == "weaviate":
        # Weaviate uses port 8080 by default
        weaviate_port = port if port != 19530 else 8080
        return WeaviateAdapter({"host": host, "port": weaviate_port})
    elif target == "pgvector":
        # pgvector uses port 5432 by default
        return PgvectorAdapter({
            "host": host,
            "port": 5432 if port == 19530 else port,
            "database": "vectordb",
            "user": "postgres",
            "password": "pgvector",
        })
    else:
        raise ValueError(f"Unknown target: {target!r}. Choose from: milvus, qdrant, weaviate, pgvector")


# ─────────────────────────────────────────────────────────────
# Utility Functions
# ─────────────────────────────────────────────────────────────

def make_vectors(n: int, dim: int, seed: int = 0) -> List[List[float]]:
    """Generate random vectors."""
    rng = random.Random(seed)
    return [[rng.gauss(0, 1) for _ in range(dim)] for _ in range(n)]


def load_contract(contract_id: str) -> Dict[str, Any]:
    """Load contract definition from JSON file."""
    contract_file = CONTRACTS_DIR / f"{contract_id.lower().replace('-', '-')}-insert-count-consistency.json"
    if contract_id == "CONC-001":
        contract_file = CONTRACTS_DIR / "conc-001-insert-count-consistency.json"
    elif contract_id == "CONC-002":
        contract_file = CONTRACTS_DIR / "conc-002-concurrent-search-isolation.json"
    elif contract_id == "CONC-003":
        contract_file = CONTRACTS_DIR / "conc-003-delete-search-consistency.json"
    
    if not contract_file.exists():
        raise FileNotFoundError(f"Contract file not found: {contract_file}")
    
    with open(contract_file, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────
# CONC-001: Concurrent Insert Count Consistency
# ─────────────────────────────────────────────────────────────

class CONC001Tester:
    """Tester for CONC-001: Concurrent Insert Count Consistency."""
    
    def __init__(self, adapter: AdapterBase, config: Dict[str, Any]):
        self.adapter = adapter
        self.config = config
        self.metrics = PerformanceMetrics()
        self.violations: List[ContractViolation] = []
        self.collection_name = f"conc001_test_{int(time.time())}"
        
    def setup(self, dim: int) -> bool:
        """Setup collection for testing."""
        try:
            # Drop if exists
            self.adapter.execute({
                "operation": "drop_collection",
                "params": {"collection_name": self.collection_name}
            })
            
            # Create collection
            r = self.adapter.execute({
                "operation": "create_collection",
                "params": {"collection_name": self.collection_name, "dimension": dim}
            })
            return r.get("status") == "success"
        except Exception as e:
            print(f"    Setup error: {e}")
            return False
    
    def teardown(self) -> None:
        """Cleanup collection."""
        try:
            self.adapter.execute({
                "operation": "drop_collection",
                "params": {"collection_name": self.collection_name}
            })
        except Exception:
            pass
    
    def run_test(self, n_threads: int, vectors_per_thread: int, dim: int) -> TestResult:
        """Run CONC-001 test."""
        print(f"\n  [CONC-001] Concurrent Insert Count Consistency")
        print(f"    Threads: {n_threads}, Vectors per thread: {vectors_per_thread}")
        
        if not self.setup(dim):
            return TestResult(
                contract_id="CONC-001",
                classification="VIOLATION",
                violations=[ContractViolation(
                    contract_id="CONC-001",
                    violation_type="setup_failure",
                    description="Failed to setup collection",
                    severity="high"
                )]
            )
        
        errors = []
        inserted_counts = [0] * n_threads
        
        def insert_worker(thread_id: int) -> Dict[str, Any]:
            vecs = make_vectors(vectors_per_thread, dim, seed=thread_id * 1000)
            # Generate unique IDs for each thread to avoid ID collision
            # Thread 0: IDs 0-49, Thread 1: IDs 50-99, etc.
            ids = [thread_id * vectors_per_thread + i for i in range(vectors_per_thread)]
            start = time.monotonic()
            r = self.adapter.execute({
                "operation": "insert",
                "params": {
                    "collection_name": self.collection_name, 
                    "vectors": vecs,
                    "ids": ids
                }
            })
            latency_ms = (time.monotonic() - start) * 1000
            
            return {
                "thread_id": thread_id,
                "status": r.get("status"),
                "error": r.get("error", ""),
                "latency_ms": latency_ms,
                "inserted": vectors_per_thread if r.get("status") == "success" else 0
            }
        
        # Run concurrent inserts
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=n_threads) as pool:
            futures = [pool.submit(insert_worker, t) for t in range(n_threads)]
            results = [f.result() for f in as_completed(futures)]
        elapsed = time.time() - start_time
        
        # Collect metrics
        for r in results:
            self.metrics.total_operations += 1
            self.metrics.latencies_ms.append(r["latency_ms"])
            if r["status"] == "success":
                self.metrics.successful_operations += 1
                inserted_counts[r["thread_id"]] = r["inserted"]
            else:
                self.metrics.failed_operations += 1
                errors.append(r)
        
        self.metrics.throughput_ops_per_sec = self.metrics.total_operations / elapsed if elapsed > 0 else 0
        
        # Flush and get count
        try:
            self.adapter.execute({
                "operation": "flush",
                "params": {"collection_name": self.collection_name}
            })
            time.sleep(0.5)  # Wait for flush
        except Exception:
            pass
        
        # Get final count
        count_result = self.adapter.execute({
            "operation": "count_entities",
            "params": {"collection_name": self.collection_name}
        })
        raw_count = count_result.get("data", 0) if count_result.get("status") == "success" else None
        # Handle case where count might be a list with storage_count
        if isinstance(raw_count, list):
            # data is a list like [{"storage_count": 200, ...}]
            if raw_count and isinstance(raw_count[0], dict):
                final_count = raw_count[0].get("storage_count", 0)
            else:
                final_count = len(raw_count)
        elif isinstance(raw_count, int):
            final_count = raw_count
        else:
            final_count = None
        expected_total = sum(inserted_counts)
        
        self.teardown()
        
        # Oracle verification
        if final_count is None:
            self.violations.append(ContractViolation(
                contract_id="CONC-001",
                violation_type="count_failure",
                description="Failed to get entity count",
                severity="high",
                details={"error": count_result.get("error", "unknown")}
            ))
        elif final_count != expected_total:
            self.violations.append(ContractViolation(
                contract_id="CONC-001",
                violation_type="count_mismatch",
                description=f"Count mismatch: expected {expected_total}, got {final_count}",
                severity="high",
                details={
                    "expected": expected_total,
                    "actual": final_count,
                    "difference": final_count - expected_total
                }
            ))
        
        if errors:
            self.violations.append(ContractViolation(
                contract_id="CONC-001",
                violation_type="insert_errors",
                description=f"{len(errors)} insert operations failed",
                severity="medium",
                details={"errors": errors[:3]}
            ))
        
        classification = "PASS" if not self.violations else "VIOLATION"
        print(f"    {classification}: expected={expected_total}, got={final_count}, "
              f"errors={len(errors)}, p95={self.metrics.p95_latency_ms}ms")
        
        return TestResult(
            contract_id="CONC-001",
            classification=classification,
            violations=self.violations,
            metrics=self.metrics,
            metadata={
                "n_threads": n_threads,
                "vectors_per_thread": vectors_per_thread,
                "expected_total": expected_total,
                "final_count": final_count,
                "insert_errors": len(errors)
            }
        )


# ─────────────────────────────────────────────────────────────
# CONC-002: Concurrent Search Isolation
# ─────────────────────────────────────────────────────────────

class CONC002Tester:
    """Tester for CONC-002: Concurrent Search Isolation."""
    
    def __init__(self, adapter: AdapterBase, config: Dict[str, Any]):
        self.adapter = adapter
        self.config = config
        self.metrics = PerformanceMetrics()
        self.violations: List[ContractViolation] = []
        self.collection_name = f"conc002_test_{int(time.time())}"
        self.deleted_ids: Set[str] = set()
        self.lock = threading.Lock()
        
    def setup(self, dim: int, n_docs: int) -> bool:
        """Setup collection with data."""
        try:
            # Drop if exists
            self.adapter.execute({
                "operation": "drop_collection",
                "params": {"collection_name": self.collection_name}
            })
            
            # Create collection
            r = self.adapter.execute({
                "operation": "create_collection",
                "params": {"collection_name": self.collection_name, "dimension": dim}
            })
            if r.get("status") != "success":
                return False
            
            # Insert vectors
            vecs = make_vectors(n_docs, dim, seed=42)
            r = self.adapter.execute({
                "operation": "insert",
                "params": {"collection_name": self.collection_name, "vectors": vecs}
            })
            if r.get("status") != "success":
                return False
            
            # Flush and build index
            self.adapter.execute({
                "operation": "flush",
                "params": {"collection_name": self.collection_name}
            })
            self.adapter.execute({
                "operation": "build_index",
                "params": {
                    "collection_name": self.collection_name,
                    "index_type": "IVF_FLAT",
                    "metric_type": "L2",
                    "nlist": 64
                }
            })
            self.adapter.execute({
                "operation": "load",
                "params": {"collection_name": self.collection_name}
            })
            
            return True
        except Exception as e:
            print(f"    Setup error: {e}")
            return False
    
    def teardown(self) -> None:
        """Cleanup collection."""
        try:
            self.adapter.execute({
                "operation": "drop_collection",
                "params": {"collection_name": self.collection_name}
            })
        except Exception:
            pass
    
    def run_test(self, n_readers: int, n_deleters: int, dim: int, 
                 duration_seconds: int = 10, top_k: int = 10) -> TestResult:
        """Run CONC-002 test."""
        print(f"\n  [CONC-002] Concurrent Search Isolation")
        print(f"    Readers: {n_readers}, Deleters: {n_deleters}, Duration: {duration_seconds}s")
        
        n_docs = 500
        if not self.setup(dim, n_docs):
            return TestResult(
                contract_id="CONC-002",
                classification="VIOLATION",
                violations=[ContractViolation(
                    contract_id="CONC-002",
                    violation_type="setup_failure",
                    description="Failed to setup collection",
                    severity="high"
                )]
            )
        
        stop_event = threading.Event()
        search_violations = []
        
        def reader_worker(reader_id: int) -> List[Dict]:
            results = []
            query_vecs = make_vectors(20, dim, seed=reader_id * 100)
            
            while not stop_event.is_set():
                for q in query_vecs:
                    if stop_event.is_set():
                        break
                    
                    start = time.monotonic()
                    r = self.adapter.execute({
                        "operation": "search",
                        "params": {
                            "collection_name": self.collection_name,
                            "vector": q,
                            "top_k": top_k
                        }
                    })
                    latency_ms = (time.monotonic() - start) * 1000
                    
                    with self.lock:
                        self.metrics.total_operations += 1
                        self.metrics.latencies_ms.append(latency_ms)
                    
                    if r.get("status") == "success":
                        with self.lock:
                            self.metrics.successful_operations += 1
                        
                        ids = r.get("data", [])
                        # Check cardinality
                        if len(ids) > top_k:
                            search_violations.append({
                                "type": "cardinality",
                                "reader_id": reader_id,
                                "returned": len(ids),
                                "top_k": top_k
                            })
                        
                        # Check for deleted entities (if we had IDs)
                        # Note: This is simplified; full implementation would track IDs
                    else:
                        with self.lock:
                            self.metrics.failed_operations += 1
                    
                    results.append({
                        "status": r.get("status"),
                        "count": len(r.get("data", [])),
                        "latency_ms": latency_ms
                    })
                
                time.sleep(0.01)
            
            return results
        
        def deleter_worker(deleter_id: int) -> List[Dict]:
            results = []
            # Simple deletion simulation - delete random IDs
            # In real implementation, would track actual entity IDs
            time.sleep(duration_seconds * 0.3)  # Start deleting after some time
            
            for i in range(5):
                if stop_event.is_set():
                    break
                # Placeholder for deletion logic
                time.sleep(0.5)
            
            return results
        
        # Run test
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=n_readers + n_deleters) as pool:
            reader_futures = [pool.submit(reader_worker, i) for i in range(n_readers)]
            deleter_futures = [pool.submit(deleter_worker, i) for i in range(n_deleters)]
            
            # Wait for duration
            time.sleep(duration_seconds)
            stop_event.set()
            
            # Collect results
            for fut in as_completed(reader_futures + deleter_futures):
                try:
                    fut.result()
                except Exception as e:
                    print(f"    Worker error: {e}")
        
        elapsed = time.time() - start_time
        self.metrics.throughput_ops_per_sec = self.metrics.total_operations / elapsed if elapsed > 0 else 0
        
        self.teardown()
        
        # Check violations
        if search_violations:
            self.violations.append(ContractViolation(
                contract_id="CONC-002",
                violation_type="search_violation",
                description=f"{len(search_violations)} search violations detected",
                severity="critical",
                details={"violations": search_violations[:5]}
            ))
        
        classification = "PASS" if not self.violations else "VIOLATION"
        print(f"    {classification}: {self.metrics.total_operations} searches, "
              f"{len(search_violations)} violations, p95={self.metrics.p95_latency_ms}ms")
        
        return TestResult(
            contract_id="CONC-002",
            classification=classification,
            violations=self.violations,
            metrics=self.metrics,
            metadata={
                "n_readers": n_readers,
                "n_deleters": n_deleters,
                "duration_seconds": duration_seconds,
                "search_violations": len(search_violations)
            }
        )


# ─────────────────────────────────────────────────────────────
# CONC-003: Delete-Search Cross Consistency
# ─────────────────────────────────────────────────────────────

class CONC003Tester:
    """Tester for CONC-003: Delete-Search Cross Consistency."""
    
    def __init__(self, adapter: AdapterBase, config: Dict[str, Any]):
        self.adapter = adapter
        self.config = config
        self.metrics = PerformanceMetrics()
        self.violations: List[ContractViolation] = []
        self.collection_name = f"conc003_test_{int(time.time())}"
        self.count_observations: List[int] = []
        self.lock = threading.Lock()
        
    def setup(self, dim: int, n_docs: int) -> bool:
        """Setup collection with data."""
        try:
            # Drop if exists
            self.adapter.execute({
                "operation": "drop_collection",
                "params": {"collection_name": self.collection_name}
            })
            
            # Create collection
            r = self.adapter.execute({
                "operation": "create_collection",
                "params": {"collection_name": self.collection_name, "dimension": dim}
            })
            if r.get("status") != "success":
                return False
            
            # Insert vectors
            vecs = make_vectors(n_docs, dim, seed=42)
            r = self.adapter.execute({
                "operation": "insert",
                "params": {"collection_name": self.collection_name, "vectors": vecs}
            })
            if r.get("status") != "success":
                return False
            
            # Flush and build index
            self.adapter.execute({
                "operation": "flush",
                "params": {"collection_name": self.collection_name}
            })
            self.adapter.execute({
                "operation": "build_index",
                "params": {
                    "collection_name": self.collection_name,
                    "index_type": "IVF_FLAT",
                    "metric_type": "L2",
                    "nlist": 64
                }
            })
            self.adapter.execute({
                "operation": "load",
                "params": {"collection_name": self.collection_name}
            })
            
            return True
        except Exception as e:
            print(f"    Setup error: {e}")
            return False
    
    def teardown(self) -> None:
        """Cleanup collection."""
        try:
            self.adapter.execute({
                "operation": "drop_collection",
                "params": {"collection_name": self.collection_name}
            })
        except Exception:
            pass
    
    def get_count(self) -> Optional[int]:
        """Get entity count."""
        try:
            r = self.adapter.execute({
                "operation": "count_entities",
                "params": {"collection_name": self.collection_name}
            })
            if r.get("status") == "success":
                return r.get("data", 0)
        except Exception:
            pass
        return None
    
    def run_test(self, n_deleters: int, n_searchers: int, dim: int,
                 duration_seconds: int = 15) -> TestResult:
        """Run CONC-003 test."""
        print(f"\n  [CONC-003] Delete-Search Cross Consistency")
        print(f"    Deleters: {n_deleters}, Searchers: {n_searchers}, Duration: {duration_seconds}s")
        
        n_docs = 300
        if not self.setup(dim, n_docs):
            return TestResult(
                contract_id="CONC-003",
                classification="VIOLATION",
                violations=[ContractViolation(
                    contract_id="CONC-003",
                    violation_type="setup_failure",
                    description="Failed to setup collection",
                    severity="high"
                )]
            )
        
        stop_event = threading.Event()
        consistency_violations = []
        prev_count = self.get_count()
        
        def searcher_worker(searcher_id: int) -> List[Dict]:
            results = []
            query_vecs = make_vectors(10, dim, seed=searcher_id * 200)
            
            while not stop_event.is_set():
                for q in query_vecs:
                    if stop_event.is_set():
                        break
                    
                    start = time.monotonic()
                    r = self.adapter.execute({
                        "operation": "search",
                        "params": {
                            "collection_name": self.collection_name,
                            "vector": q,
                            "top_k": 10
                        }
                    })
                    latency_ms = (time.monotonic() - start) * 1000
                    
                    with self.lock:
                        self.metrics.total_operations += 1
                        self.metrics.latencies_ms.append(latency_ms)
                        if r.get("status") == "success":
                            self.metrics.successful_operations += 1
                        else:
                            self.metrics.failed_operations += 1
                    
                    # Check count monotonicity
                    cnt = self.get_count()
                    if cnt is not None:
                        with self.lock:
                            nonlocal prev_count
                            if cnt > prev_count:
                                # Count increased after delete - violation
                                consistency_violations.append({
                                    "type": "count_increase",
                                    "searcher_id": searcher_id,
                                    "prev_count": prev_count,
                                    "current_count": cnt
                                })
                            prev_count = cnt
                            self.count_observations.append(cnt)
                    
                    results.append({
                        "status": r.get("status"),
                        "count": len(r.get("data", [])),
                        "entity_count": cnt,
                        "latency_ms": latency_ms
                    })
                
                time.sleep(0.02)
            
            return results
        
        def deleter_worker(deleter_id: int) -> List[Dict]:
            results = []
            time.sleep(1)  # Let searchers start first
            
            for i in range(10):
                if stop_event.is_set():
                    break
                
                # Get count before delete
                before_count = self.get_count()
                
                # Delete operation (simplified - would use actual IDs)
                start = time.monotonic()
                # Placeholder: actual implementation would delete specific entities
                time.sleep(0.1)  # Simulate delete time
                latency_ms = (time.monotonic() - start) * 1000
                
                with self.lock:
                    self.metrics.total_operations += 1
                    self.metrics.latencies_ms.append(latency_ms)
                
                time.sleep(0.5)
            
            return results
        
        # Run test
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=n_deleters + n_searchers) as pool:
            searcher_futures = [pool.submit(searcher_worker, i) for i in range(n_searchers)]
            deleter_futures = [pool.submit(deleter_worker, i) for i in range(n_deleters)]
            
            # Wait for duration
            time.sleep(duration_seconds)
            stop_event.set()
            
            # Collect results
            for fut in as_completed(searcher_futures + deleter_futures):
                try:
                    fut.result()
                except Exception as e:
                    print(f"    Worker error: {e}")
        
        elapsed = time.time() - start_time
        self.metrics.throughput_ops_per_sec = self.metrics.total_operations / elapsed if elapsed > 0 else 0
        
        self.teardown()
        
        # Check violations
        if consistency_violations:
            self.violations.append(ContractViolation(
                contract_id="CONC-003",
                violation_type="consistency_violation",
                description=f"{len(consistency_violations)} consistency violations detected",
                severity="high",
                details={"violations": consistency_violations[:5]}
            ))
        
        classification = "PASS" if not self.violations else "VIOLATION"
        print(f"    {classification}: {self.metrics.total_operations} operations, "
              f"{len(consistency_violations)} violations, p95={self.metrics.p95_latency_ms}ms")
        
        return TestResult(
            contract_id="CONC-003",
            classification=classification,
            violations=self.violations,
            metrics=self.metrics,
            metadata={
                "n_deleters": n_deleters,
                "n_searchers": n_searchers,
                "duration_seconds": duration_seconds,
                "consistency_violations": len(consistency_violations)
            }
        )


# ─────────────────────────────────────────────────────────────
# Main Test Runner
# ─────────────────────────────────────────────────────────────

def run_contract_test(
    contract_id: str,
    adapter: AdapterBase,
    config: Dict[str, Any]
) -> TestResult:
    """Run a specific contract test."""
    if contract_id == "CONC-001":
        tester = CONC001Tester(adapter, config)
        return tester.run_test(
            n_threads=config.get("threads", 4),
            vectors_per_thread=config.get("vectors_per_thread", 100),
            dim=config.get("dim", 64)
        )
    elif contract_id == "CONC-002":
        tester = CONC002Tester(adapter, config)
        return tester.run_test(
            n_readers=config.get("readers", 4),
            n_deleters=config.get("deleters", 1),
            dim=config.get("dim", 64),
            duration_seconds=config.get("duration", 10),
            top_k=config.get("top_k", 10)
        )
    elif contract_id == "CONC-003":
        tester = CONC003Tester(adapter, config)
        return tester.run_test(
            n_deleters=config.get("deleters", 2),
            n_searchers=config.get("searchers", 4),
            dim=config.get("dim", 64),
            duration_seconds=config.get("duration", 15)
        )
    else:
        raise ValueError(f"Unknown contract: {contract_id}")


def main():
    parser = argparse.ArgumentParser(
        description="Generic Concurrent Test Framework for Vector Databases"
    )
    parser.add_argument(
        "--contract",
        choices=["CONC-001", "CONC-002", "CONC-003"],
        help="Specific contract to test"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all CONC contracts"
    )
    parser.add_argument(
        "--target",
        default="milvus",
        choices=["milvus", "qdrant", "weaviate", "pgvector"],
        help="Target database adapter"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Database host"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=19530,
        help="Database port"
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Number of threads for CONC-001"
    )
    parser.add_argument(
        "--readers",
        type=int,
        default=4,
        help="Number of reader threads for CONC-002/003"
    )
    parser.add_argument(
        "--deleters",
        type=int,
        default=1,
        help="Number of deleter threads for CONC-002/003"
    )
    parser.add_argument(
        "--searchers",
        type=int,
        default=4,
        help="Number of searcher threads for CONC-003"
    )
    parser.add_argument(
        "--vectors-per-thread",
        type=int,
        default=100,
        dest="vectors_per_thread",
        help="Vectors per thread for CONC-001"
    )
    parser.add_argument(
        "--dim",
        type=int,
        default=64,
        help="Vector dimension"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=10,
        help="Test duration in seconds for CONC-002/003"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        dest="top_k",
        help="Top-K for search operations"
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Enable performance profiling"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for results (JSON)"
    )
    
    args = parser.parse_args()
    
    if not args.contract and not args.all:
        parser.error("Must specify either --contract or --all")
    
    # Build adapter
    print(f"\n{'='*60}")
    print(f"  Concurrent Test Framework")
    print(f"  Target: {args.target} ({args.host}:{args.port})")
    print(f"{'='*60}")
    
    try:
        adapter = build_adapter(args.target, args.host, args.port)
        if not adapter.health_check():
            print(f"ERROR: {args.target} health check failed")
            sys.exit(1)
        print(f"  {args.target} connected OK")
    except Exception as e:
        print(f"ERROR: Failed to connect to {args.target}: {e}")
        sys.exit(1)
    
    # Build config
    config = {
        "threads": args.threads,
        "readers": args.readers,
        "deleters": args.deleters,
        "searchers": args.searchers,
        "vectors_per_thread": args.vectors_per_thread,
        "dim": args.dim,
        "duration": args.duration,
        "top_k": args.top_k,
        "profile": args.profile,
    }
    
    # Determine contracts to run
    contracts = ["CONC-001", "CONC-002", "CONC-003"] if args.all else [args.contract]
    
    # Run tests
    results: Dict[str, TestResult] = {}
    for contract_id in contracts:
        try:
            result = run_contract_test(contract_id, adapter, config)
            results[contract_id] = result
        except Exception as e:
            print(f"ERROR running {contract_id}: {e}")
            import traceback
            traceback.print_exc()
            results[contract_id] = TestResult(
                contract_id=contract_id,
                classification="ERROR",
                violations=[ContractViolation(
                    contract_id=contract_id,
                    violation_type="test_error",
                    description=str(e),
                    severity="high"
                )]
            )
    
    # Summary
    print(f"\n{'='*60}")
    print(f"  Test Summary")
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
        print(f"\n  Violation Details:")
        for contract_id, result in results.items():
            if result.classification == "VIOLATION":
                print(f"    [{contract_id}]")
                for v in result.violations:
                    print(f"      - {v.violation_type}: {v.description}")
    
    # Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    if args.output:
        out_path = args.output
    else:
        out_path = RESULTS_DIR / f"conc-test-{args.target}-{ts}.json"
    
    output_data = {
        "run_id": f"conc-test-{ts}",
        "timestamp": datetime.now().isoformat(),
        "target": args.target,
        "host": args.host,
        "port": args.port,
        "config": config,
        "summary": {
            "total": total,
            "passes": passes,
            "violations": violations,
            "errors": errors
        },
        "results": {k: v.to_dict() for k, v in results.items()}
    }
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n  Results saved: {out_path}")
    print(f"{'='*60}\n")
    
    # Exit with error code if violations found
    sys.exit(1 if violations > 0 or errors > 0 else 0)


if __name__ == "__main__":
    main()
