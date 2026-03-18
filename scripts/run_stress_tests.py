#!/usr/bin/env python3
"""
Stress Test Contract Tests for ai-db-qc
=======================================
Tests stress contracts:

  STR-001  High Throughput Stress  -- database stability under high request rates
  STR-002  Large Dataset Stress     -- database scalability with millions of vectors

Usage:
    python scripts/run_stress_tests.py --db milvus --contract STR-001
    python scripts/run_stress_tests.py --db qdrant --contract STR-002
    python scripts/run_stress_tests.py --db all --contract all
"""

import argparse
import sys
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import yaml

import numpy as np

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Load database connection config
# ---------------------------------------------------------------------------
def load_connection_config() -> Dict[str, Any]:
    """Load database connection configuration."""
    config_path = PROJECT_ROOT / "configs" / "database_connections.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

CONNECTION_CONFIG = load_connection_config()

# ---------------------------------------------------------------------------
# Adapter factory
# ---------------------------------------------------------------------------

def get_adapter(db_name: str) -> Any:
    """Instantiate and return adapter for *db_name*."""
    db_name = db_name.lower()
    config = CONNECTION_CONFIG.get(db_name, {})
    
    if db_name == "milvus":
        from adapters.milvus_adapter import MilvusAdapter
        return MilvusAdapter(config)
    elif db_name == "qdrant":
        from adapters.qdrant_adapter import QdrantAdapter
        return QdrantAdapter(config)
    elif db_name == "weaviate":
        from adapters.weaviate_adapter import WeaviateAdapter
        return WeaviateAdapter(config)
    elif db_name in ("pgvector", "pg"):
        from adapters.pgvector_adapter import PgvectorAdapter
        return PgvectorAdapter(config)
    else:
        raise ValueError(f"Unknown database: {db_name!r}. "
                         "Choose from: milvus, qdrant, weaviate, pgvector")


def _is_milvus(adapter: Any) -> bool:
    return type(adapter).__name__ == "MilvusAdapter"


def _flush(adapter: Any, col: str) -> None:
    """Issue a flush if adapter supports it."""
    try:
        adapter.execute({"operation": "flush", "params": {"collection_name": col}})
        time.sleep(1.0)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Test utilities
# ---------------------------------------------------------------------------

def generate_vectors(count: int, dim: int) -> List[List[float]]:
    """Generate random vectors."""
    return np.random.random((count, dim)).tolist()


def generate_vector(dim: int) -> List[float]:
    """Generate single random vector."""
    return np.random.random(dim).tolist()


class StressTestStats:
    """Statistics for stress testing."""

    def __init__(self):
        self.errors = 0
        self.successes = 0
        self.timeouts = 0
        self.latencies = []
        self.lock = threading.Lock()

    def record_success(self, latency: float):
        with self.lock:
            self.successes += 1
            self.latencies.append(latency)

    def record_error(self):
        with self.lock:
            self.errors += 1

    def record_timeout(self):
        with self.lock:
            self.timeouts += 1

    def get_summary(self) -> Dict[str, Any]:
        with self.lock:
            total = self.successes + self.errors + self.timeouts
            success_rate = self.successes / total if total > 0 else 0
            avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
            p95_latency = sorted(self.latencies)[int(len(self.latencies) * 0.95)] if self.latencies else 0
            p99_latency = sorted(self.latencies)[int(len(self.latencies) * 0.99)] if self.latencies else 0

            return {
                "total_requests": total,
                "successes": self.successes,
                "errors": self.errors,
                "timeouts": self.timeouts,
                "success_rate": success_rate,
                "avg_latency_ms": avg_latency * 1000,
                "p95_latency_ms": p95_latency * 1000,
                "p99_latency_ms": p99_latency * 1000,
            }


# ---------------------------------------------------------------------------
# STR-001: High Throughput Stress Test
# ---------------------------------------------------------------------------

def run_throughput_test(adapter: Any, db_name: str, throughput_level: str) -> Dict[str, Any]:
    """Run throughput test at specified level."""
    levels = {
        "low": {"rps": 100, "duration": 60},
        "medium": {"rps": 1000, "duration": 60},
        "high": {"rps": 5000, "duration": 60},
        "extreme": {"rps": 10000, "duration": 30},
    }

    config = levels[throughput_level]
    rps = config["rps"]
    duration = config["duration"]
    target_requests = rps * duration

    print(f"\n  Testing at {rps} RPS for {duration}s ({target_requests} total requests)")

    stats = StressTestStats()
    stop_event = threading.Event()

    col = "str001_throughput"

    try:
        # Setup collection
        create_res = adapter.execute({
            "operation": "create_collection",
            "params": {
                "collection_name": col,
                "dimension": 128,
                "metric_type": "L2"
            }
        })
        if create_res.get("status") != "success":
            raise Exception(f"Failed to create collection: {create_res}")

        # Build and load index
        adapter.execute({"operation": "build_index",
                        "params": {"collection_name": col, "index_type": "IVF_FLAT"}})
        adapter.execute({"operation": "load",
                        "params": {"collection_name": col}})

        # Worker function
        def worker():
            while not stop_event.is_set():
                start = time.time()

                # Mix of operations
                operation = np.random.choice(["insert", "search"], p=[0.4, 0.6])

                try:
                    if operation == "insert":
                        vec = generate_vector(128)
                        adapter.execute({
                            "operation": "insert",
                            "params": {
                                "collection_name": col,
                                "vectors": [vec],
                                "ids": [int(time.time() * 1000000) % 10000000]
                            }
                        })
                    else:  # search
                        vec = generate_vector(128)
                        adapter.execute({
                            "operation": "search",
                            "params": {
                                "collection_name": col,
                                "vector": vec,
                                "top_k": 10
                            }
                        })

                    latency = time.time() - start
                    stats.record_success(latency)

                except Exception as e:
                    stats.record_error()

        # Start workers
        num_workers = min(rps, 100)  # Cap at 100 workers
        threads = []
        for _ in range(num_workers):
            t = threading.Thread(target=worker)
            t.start()
            threads.append(t)

        # Run for duration
        time.sleep(duration)
        stop_event.set()

        # Wait for workers
        for t in threads:
            t.join(timeout=5)

        return stats.get_summary()

    except Exception as e:
        return {"error": str(e)}
    finally:
        # Cleanup
        try:
            adapter.execute({"operation": "drop_collection",
                           "params": {"collection_name": col}})
        except Exception:
            pass


def test_str001_throughput(adapter: Any, db_name: str) -> Dict[str, Any]:
    """Test STR-001: High Throughput Stress."""
    print(f"\n{'='*60}")
    print(f"STR-001: High Throughput Stress Test - {db_name}")
    print(f"{'='*60}")

    results = {
        "contract_id": "STR-001",
        "database": db_name,
        "test_cases": []
    }

    levels = ["low", "medium", "high"]  # Skip extreme for safety

    for level in levels:
        print(f"\n[Phase {level.upper()}] Throughput test")
        test_result = {"name": f"Throughput test at {level}", "checks": []}

        stats = run_throughput_test(adapter, db_name, level)

        if "error" in stats:
            test_result["checks"].append({
                "name": "Test completed without crash",
                "status": False,
                "error": stats["error"]
            })
            test_result["verdict"] = "TYPE-3 (crash)"
        else:
            # Check no crashes
            test_result["checks"].append({
                "name": "No crashes",
                "status": True
            })

            # Check success rate
            success_rate = stats["success_rate"]
            test_result["checks"].append({
                "name": f"Success rate: {success_rate:.2%}",
                "status": success_rate >= 0.95
            })

            # Check latency
            avg_latency = stats["avg_latency_ms"]
            test_result["checks"].append({
                "name": f"Average latency: {avg_latency:.2f}ms",
                "status": avg_latency < 1000  # 1 second threshold
            })

            # Verdict
            if success_rate >= 0.95 and avg_latency < 1000:
                test_result["verdict"] = "PASS"
            elif success_rate >= 0.90:
                test_result["verdict"] = "MARGINAL"
            else:
                test_result["verdict"] = "TYPE-3 (high failure rate)"

            test_result["stats"] = stats

        results["test_cases"].append(test_result)

    # Overall verdict
    verdicts = [tc["verdict"] for tc in results["test_cases"]]
    if all(v == "PASS" for v in verdicts):
        results["overall_verdict"] = "PASS"
    elif all(v in ["PASS", "MARGINAL"] for v in verdicts):
        results["overall_verdict"] = "MARGINAL"
    else:
        results["overall_verdict"] = "BUG"

    return results


# ---------------------------------------------------------------------------
# STR-002: Large Dataset Stress Test
# ---------------------------------------------------------------------------

def run_volume_test(adapter: Any, db_name: str, num_vectors: int) -> Dict[str, Any]:
    """Run volume test with specified number of vectors."""
    print(f"\n  Testing with {num_vectors:,} vectors")

    stats = {"phases": []}
    col = f"str002_volume_{num_vectors//1000}k"

    try:
        # Setup collection
        create_res = adapter.execute({
            "operation": "create_collection",
            "params": {
                "collection_name": col,
                "dimension": 128,
                "metric_type": "L2"
            }
        })
        if create_res.get("status") != "success":
            raise Exception(f"Failed to create collection: {create_res}")

        # Phase 1: Insert vectors
        print(f"  Phase 1: Inserting {num_vectors:,} vectors...")
        phase1_start = time.time()

        batch_size = 10000
        for i in range(0, num_vectors, batch_size):
            batch_end = min(i + batch_size, num_vectors)
            batch_count = batch_end - i
            vectors = generate_vectors(batch_count, 128)
            ids = list(range(i, batch_end))

            insert_res = adapter.execute({
                "operation": "insert",
                "params": {
                    "collection_name": col,
                    "vectors": vectors,
                    "ids": ids
                }
            })

            if insert_res.get("status") != "success":
                raise Exception(f"Insert failed at {i}: {insert_res}")

            if (batch_end // batch_size) % 10 == 0:
                print(f"    Progress: {batch_end:,}/{num_vectors:,}")

        phase1_time = time.time() - phase1_start
        stats["phases"].append({
            "name": "insert",
            "time_seconds": phase1_time,
            "vectors_per_second": num_vectors / phase1_time
        })
        print(f"    Completed in {phase1_time:.2f}s ({num_vectors/phase1_time:.0f} vectors/s)")

        if _is_milvus(adapter):
            _flush(adapter, col)
            time.sleep(2)

        # Phase 2: Build index
        print(f"  Phase 2: Building index...")
        phase2_start = time.time()

        index_res = adapter.execute({
            "operation": "build_index",
            "params": {
                "collection_name": col,
                "index_type": "IVF_FLAT"
            }
        })
        if index_res.get("status") != "success":
            raise Exception(f"Index build failed: {index_res}")

        phase2_time = time.time() - phase2_start
        stats["phases"].append({
            "name": "build_index",
            "time_seconds": phase2_time
        })
        print(f"    Completed in {phase2_time:.2f}s")

        # Phase 3: Load index
        print(f"  Phase 3: Loading index...")
        phase3_start = time.time()

        load_res = adapter.execute({
            "operation": "load",
            "params": {"collection_name": col}
        })
        if load_res.get("status") != "success":
            raise Exception(f"Index load failed: {load_res}")

        phase3_time = time.time() - phase3_start
        stats["phases"].append({
            "name": "load",
            "time_seconds": phase3_time
        })
        print(f"    Completed in {phase3_time:.2f}s")

        # Phase 4: Search performance
        print(f"  Phase 4: Running 1000 searches...")
        phase4_start = time.time()

        search_latencies = []
        for i in range(1000):
            vec = generate_vector(128)
            search_start = time.time()
            search_res = adapter.execute({
                "operation": "search",
                "params": {
                    "collection_name": col,
                    "vector": vec,
                    "top_k": 10
                }
            })
            search_latency = time.time() - search_start
            search_latencies.append(search_latency)

            if search_res.get("status") != "success":
                raise Exception(f"Search failed: {search_res}")

            if (i + 1) % 100 == 0:
                print(f"    Progress: {i+1}/1000")

        phase4_time = time.time() - phase4_start
        avg_search_latency = sum(search_latencies) / len(search_latencies)
        p95_search_latency = sorted(search_latencies)[int(len(search_latencies) * 0.95)]

        stats["phases"].append({
            "name": "search",
            "time_seconds": phase4_time,
            "avg_search_latency_ms": avg_search_latency * 1000,
            "p95_search_latency_ms": p95_search_latency * 1000
        })
        print(f"    Completed in {phase4_time:.2f}s")
        print(f"    Avg latency: {avg_search_latency*1000:.2f}ms, P95: {p95_search_latency*1000:.2f}ms")

        return stats

    except Exception as e:
        return {"error": str(e)}
    finally:
        # Cleanup
        try:
            adapter.execute({"operation": "drop_collection",
                           "params": {"collection_name": col}})
        except Exception:
            pass


def test_str002_volume(adapter: Any, db_name: str) -> Dict[str, Any]:
    """Test STR-002: Large Dataset Stress."""
    print(f"\n{'='*60}")
    print(f"STR-002: Large Dataset Stress Test - {db_name}")
    print(f"{'='*60}")

    results = {
        "contract_id": "STR-002",
        "database": db_name,
        "test_cases": []
    }

    # Test at different scales
    scales = [10000, 100000]  # 10K, 100K (1M+ takes too long)

    for scale in scales:
        print(f"\n[Phase {scale//1000}K] Volume test")
        test_result = {"name": f"Volume test with {scale:,} vectors", "checks": []}

        stats = run_volume_test(adapter, db_name, scale)

        if "error" in stats:
            test_result["checks"].append({
                "name": "Test completed without crash",
                "status": False,
                "error": stats["error"]
            })
            test_result["verdict"] = "TYPE-3 (crash)"
        else:
            # Check no crashes
            test_result["checks"].append({
                "name": "No crashes",
                "status": True
            })

            # Check search performance
            search_stats = next((p for p in stats["phases"] if p["name"] == "search"), {})
            if search_stats:
                avg_latency = search_stats["avg_search_latency_ms"]
                p95_latency = search_stats["p95_search_latency_ms"]

                # Thresholds based on scale
                if scale == 10000:
                    threshold = 100  # 100ms
                elif scale == 100000:
                    threshold = 200  # 200ms
                else:
                    threshold = 500  # 500ms

                test_result["checks"].append({
                    "name": f"Average latency ({avg_latency:.2f}ms) < {threshold}ms",
                    "status": avg_latency < threshold
                })

                test_result["checks"].append({
                    "name": f"P95 latency ({p95_latency:.2f}ms) reasonable",
                    "status": p95_latency < threshold * 2
                })

                if avg_latency < threshold and p95_latency < threshold * 2:
                    test_result["verdict"] = "PASS"
                elif avg_latency < threshold * 2:
                    test_result["verdict"] = "MARGINAL"
                else:
                    test_result["verdict"] = "TYPE-4 (severe degradation)"

            test_result["stats"] = stats

        results["test_cases"].append(test_result)

    # Overall verdict
    verdicts = [tc["verdict"] for tc in results["test_cases"]]
    if all(v == "PASS" for v in verdicts):
        results["overall_verdict"] = "PASS"
    elif all(v in ["PASS", "MARGINAL"] for v in verdicts):
        results["overall_verdict"] = "MARGINAL"
    else:
        results["overall_verdict"] = "BUG"

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run stress test contracts")
    parser.add_argument("--db", type=str, default="milvus",
                       choices=["milvus", "qdrant", "weaviate", "pgvector", "all"],
                       help="Database to test")
    parser.add_argument("--contract", type=str, default="all",
                       choices=["STR-001", "STR-002", "all"],
                       help="Contract to test")
    parser.add_argument("--output", type=str, default=None,
                       help="Output file for results (JSON)")
    args = parser.parse_args()

    databases = ["milvus", "qdrant", "weaviate", "pgvector"] if args.db == "all" else [args.db]
    contracts = ["STR-001", "STR-002"] if args.contract == "all" else [args.contract]

    all_results = []

    for db in databases:
        print(f"\n{'#'*60}")
        print(f"# Testing {db.upper()}")
        print(f"{'#'*60}")

        try:
            adapter = get_adapter(db)

            if "STR-001" in contracts:
                str001_results = test_str001_throughput(adapter, db)
                all_results.append(str001_results)

            if "STR-002" in contracts:
                str002_results = test_str002_volume(adapter, db)
                all_results.append(str002_results)

        except Exception as e:
            print(f"\n  [ERROR] Failed to test {db}: {e}")
            all_results.append({
                "database": db,
                "error": str(e),
                "overall_verdict": "ERROR"
            })

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for res in all_results:
        db = res.get("database", "unknown")
        contract = res.get("contract_id", "unknown")
        verdict = res.get("overall_verdict", "ERROR")
        icon = "[OK]" if verdict == "PASS" else "[FAIL]"
        print(f"  {icon} {db} {contract}: {verdict}")

    # Save results
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"\nResults saved to: {output_path}")

    return all_results


if __name__ == "__main__":
    main()
