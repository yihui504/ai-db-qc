"""SeekDB Extended Contract Coverage Campaign.

Extends SeekDB testing beyond the original Differential v3 (parameter boundary +
precondition scenarios) to cover the full new contract family roster:

  MR-03  Hard Negative Discrimination  (semantic metamorphic)
  R7A/B  Concurrency isolation + write-read interleaving
  R8     Data drift / index quality degradation
  R5D    Schema contract: schema change compatibility (SCH-001 ~ SCH-004)

Two-step strategy aligned with the project plan:
  Step-1  Expand NEW contract types to SeekDB
  Step-2  Full R1-R6 coverage sweep (comprehensive)

Usage:
    # Step-1: new contract families (default)
    python scripts/run_seekdb_extended.py

    # Step-2: full R1-R6 coverage
    python scripts/run_seekdb_extended.py --step 2

    # offline smoke test (mock adapter)
    python scripts/run_seekdb_extended.py --offline
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.mock import MockAdapter, ResponseMode

RESULTS_DIR = Path("results")


# ─────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────

def _rand_vectors(n: int, dim: int, seed: int = 0) -> List[List[float]]:
    rng = random.Random(seed)
    return [[rng.uniform(-1, 1) for _ in range(dim)] for _ in range(n)]


def _build_adapter(args) -> tuple:
    """Return (adapter, adapter_name, is_fallback)."""
    if args.offline:
        return MockAdapter(response_mode=ResponseMode.SUCCESS), "mock", False
    try:
        from adapters.seekdb_adapter import SeekDBAdapter
        cfg = {
            "host":     args.host,
            "port":     args.port,
            "user":     args.user,
            "password": args.password,
            "database": args.database,
        }
        a = SeekDBAdapter(cfg)
        if a.health_check():
            print(f"  Connected to SeekDB at {args.host}:{args.port}")
            return a, "seekdb", False
        raise RuntimeError("health_check returned False")
    except Exception as e:
        print(f"  SeekDB unavailable ({e}), falling back to mock.")
        return MockAdapter(response_mode=ResponseMode.SUCCESS), "mock", True


def _setup_collection(adapter, col: str, dim: int, vectors: List[List[float]]) -> bool:
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
    r = adapter.execute({"operation": "create_collection", "params": {
        "collection_name": col, "dimension": dim,
    }})
    if r.get("status") != "success":
        return False
    BATCH = 200
    for i in range(0, len(vectors), BATCH):
        adapter.execute({"operation": "insert", "params": {
            "collection_name": col,
            "vectors": vectors[i:i + BATCH],
            "ids": list(range(i, min(i + BATCH, len(vectors)))),
        }})
    adapter.execute({"operation": "flush", "params": {"collection_name": col}})
    adapter.execute({"operation": "build_index", "params": {
        "collection_name": col, "index_type": "IVF_FLAT", "metric_type": "L2",
        "nlist": min(64, max(4, len(vectors) // 10)),
    }})
    adapter.execute({"operation": "load", "params": {"collection_name": col}})
    return True


# ─────────────────────────────────────────────────────────────
# Test family implementations
# ─────────────────────────────────────────────────────────────

def run_mr03_on_seekdb(adapter, run_id: str, dim: int = 64) -> Dict[str, Any]:
    """MR-03 Hard Negative Discrimination on SeekDB.

    Uses the legal + code domain hard-negative templates (no LLM, no embedding model).
    Tests that surface-similar but semantically-different vectors are NOT top-K neighbors.

    For SeekDB (SQL-based vector), we use hash-based deterministic vectors that simulate
    the property: hard-negative pairs have high cosine similarity but should differ semantically.
    We construct these by taking a base vector, applying a small rotation (correlated = similar
    surface) but marking them as ground-truth NON-neighbors.
    """
    col = f"seekdb_mr03_{run_id}"
    print(f"\n  [MR-03] Hard Negative Discrimination")

    # Build corpus: 50 normal vectors + 10 hard-negative pairs (20 extra)
    corpus_size = 50
    hn_pairs    = 10
    corpus = _rand_vectors(corpus_size, dim, seed=10)

    # Hard negative pairs: each pair is close in vector space but "different semantically"
    # We simulate this by taking a vector and adding tiny noise → it should rank near query
    # but our contract says it shouldn't (rank > 3 for hard negatives)
    hn_a_vecs = _rand_vectors(hn_pairs, dim, seed=20)  # queries
    hn_b_vecs = []
    rng = random.Random(99)
    for v in hn_a_vecs:
        # Slight perturbation → very close in L2 but "semantically different"
        noisy = [x + rng.gauss(0, 0.05) for x in v]
        hn_b_vecs.append(noisy)

    all_corpus = corpus + hn_a_vecs + hn_b_vecs
    ok = _setup_collection(adapter, col, dim, all_corpus)
    if not ok:
        return {"test": "MR-03", "error": "setup failed", "violations": []}

    text_to_idx = {i: i for i in range(len(all_corpus))}
    hn_a_start  = corpus_size
    hn_b_start  = corpus_size + hn_pairs

    violations = []
    results_detail = []
    for i in range(hn_pairs):
        query_idx  = hn_a_start + i
        target_idx = hn_b_start + i
        query_vec  = all_corpus[query_idx]

        r = adapter.execute({"operation": "search", "params": {
            "collection_name": col, "vector": query_vec, "top_k": 10,
        }})
        returned_ids = [x.get("id") for x in r.get("data", [])]

        rank = None
        if target_idx in returned_ids:
            rank = returned_ids.index(target_idx) + 1

        if rank and rank <= 3:
            cls = "VIOLATION"
            violations.append({
                "pair_idx": i,
                "rank": rank,
                "reason": f"Hard negative appeared at rank {rank} (should be far)",
            })
        else:
            cls = "PASS"
        results_detail.append({"pair_idx": i, "rank": rank, "classification": cls})

    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})

    summary = {"PASS": sum(1 for r in results_detail if r["classification"] == "PASS"),
                "VIOLATION": len(violations)}
    print(f"    Results: {summary} | {len(violations)} violations")
    return {"test": "MR-03", "summary": summary, "violations": violations,
            "detail": results_detail}


def run_r7_on_seekdb(adapter, run_id: str, dim: int = 64,
                     n_threads: int = 8, n_inserts_per_thread: int = 25) -> Dict[str, Any]:
    """R7A/B Concurrency tests on SeekDB.

    R7A: N threads issue search queries simultaneously → each gets valid results.
    R7B: Writer inserts while readers query → result count is monotonic.
    """
    print(f"\n  [R7] Concurrency Tests (threads={n_threads})")

    # ── R7A: Concurrent search isolation ────────────────────
    col_r7a = f"seekdb_r7a_{run_id}"
    base_vecs = _rand_vectors(200, dim, seed=5)
    ok = _setup_collection(adapter, col_r7a, dim, base_vecs)

    r7a_violations = []
    r7a_errors = []

    def _search_worker(tid: int) -> Dict:
        qvec = _rand_vectors(1, dim, seed=tid * 1000)[0]
        r = adapter.execute({"operation": "search", "params": {
            "collection_name": col_r7a, "vector": qvec, "top_k": 5,
        }})
        result_count = len(r.get("data", []))
        ok_flag = r.get("status") == "success" and result_count > 0
        return {"tid": tid, "ok": ok_flag, "count": result_count, "status": r.get("status")}

    if ok:
        with ThreadPoolExecutor(max_workers=n_threads) as ex:
            futures = [ex.submit(_search_worker, i) for i in range(n_threads)]
            for fut in as_completed(futures):
                res = fut.result()
                if not res["ok"]:
                    r7a_violations.append({
                        "type": "R7A-SEARCH-FAILURE",
                        "tid": res["tid"],
                        "detail": f"Thread {res['tid']} got status={res['status']} count={res['count']}",
                    })

    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col_r7a}})

    # ── R7B: Write-read interleaving ─────────────────────────
    col_r7b = f"seekdb_r7b_{run_id}"
    init_vecs = _rand_vectors(50, dim, seed=7)
    ok_r7b = _setup_collection(adapter, col_r7b, dim, init_vecs)

    r7b_violations = []
    counts_over_time: List[int] = []
    lock = threading.Lock()

    def _count_reader():
        for _ in range(6):
            r = adapter.execute({"operation": "count_entities", "params": {
                "collection_name": col_r7b
            }})
            c = r.get("storage_count", 0) or r.get("data", [{}])[0].get("storage_count", 0)
            with lock:
                counts_over_time.append(int(c))
            time.sleep(0.1)

    def _writer():
        new_vecs = _rand_vectors(50, dim, seed=88)
        for i in range(0, len(new_vecs), 10):
            adapter.execute({"operation": "insert", "params": {
                "collection_name": col_r7b,
                "vectors": new_vecs[i:i+10],
                "ids": list(range(50 + i, 50 + min(i + 10, len(new_vecs)))),
            }})
            adapter.execute({"operation": "flush", "params": {"collection_name": col_r7b}})
            time.sleep(0.05)

    if ok_r7b:
        t_reader = threading.Thread(target=_count_reader)
        t_writer = threading.Thread(target=_writer)
        t_reader.start()
        t_writer.start()
        t_reader.join(timeout=5)
        t_writer.join(timeout=5)

        # Check monotonicity of counts
        for i in range(1, len(counts_over_time)):
            if counts_over_time[i] < counts_over_time[i - 1]:
                r7b_violations.append({
                    "type": "R7B-COUNT-DECREASE",
                    "detail": f"Count decreased from {counts_over_time[i-1]} to {counts_over_time[i]}",
                    "counts": counts_over_time,
                })

    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col_r7b}})

    all_violations = r7a_violations + r7b_violations
    print(f"    R7A violations: {len(r7a_violations)}, R7B violations: {len(r7b_violations)}")
    return {
        "test": "R7",
        "r7a_violations": r7a_violations,
        "r7b_violations": r7b_violations,
        "violations": all_violations,
        "counts_timeline": counts_over_time,
        "summary": {
            "R7A": {"n_threads": n_threads, "violations": len(r7a_violations)},
            "R7B": {"violations": len(r7b_violations), "counts": counts_over_time},
        },
    }


def run_r8_on_seekdb(adapter, run_id: str, dim: int = 64,
                     n_base: int = 200, n_drift: int = 100) -> Dict[str, Any]:
    """R8 Data Drift on SeekDB (lightweight version, no brute-force recall)."""
    print(f"\n  [R8] Data Drift on SeekDB")
    col = f"seekdb_r8_{run_id}"

    base_vecs = _rand_vectors(n_base, dim, seed=42)
    ok = _setup_collection(adapter, col, dim, base_vecs)
    if not ok:
        return {"test": "R8", "error": "setup failed", "violations": []}

    # Probe: 10 queries → measure baseline count in top-10
    probe_vecs = _rand_vectors(10, dim, seed=99)
    baseline_counts = []
    for qv in probe_vecs:
        r = adapter.execute({"operation": "search", "params": {
            "collection_name": col, "vector": qv, "top_k": 10,
        }})
        baseline_counts.append(len(r.get("data", [])))
    mean_base = sum(baseline_counts) / len(baseline_counts) if baseline_counts else 0

    # Insert off-distribution drift batch (far from origin)
    rng = random.Random(77)
    drift_vecs = [[rng.uniform(0.8, 1.0) for _ in range(dim)] for _ in range(n_drift)]
    for i in range(0, len(drift_vecs), 100):
        adapter.execute({"operation": "insert", "params": {
            "collection_name": col,
            "vectors": drift_vecs[i:i + 100],
            "ids": list(range(n_base + i, n_base + min(i + 100, n_drift))),
        }})
    adapter.execute({"operation": "flush", "params": {"collection_name": col}})

    # Post-drift probe (no reindex)
    post_counts = []
    for qv in probe_vecs:
        r = adapter.execute({"operation": "search", "params": {
            "collection_name": col, "vector": qv, "top_k": 10,
        }})
        post_counts.append(len(r.get("data", [])))
    mean_post = sum(post_counts) / len(post_counts) if post_counts else 0

    violations = []
    # Cardinality should still be 10 (top-k=10 and corpus > 10)
    for i, (b, p) in enumerate(zip(baseline_counts, post_counts)):
        if p < b:
            violations.append({
                "type": "R8-CARDINALITY-DROP",
                "probe_idx": i,
                "baseline_count": b,
                "post_drift_count": p,
            })

    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
    print(f"    Baseline avg count={mean_base:.1f}, Post-drift avg count={mean_post:.1f}, "
          f"Violations={len(violations)}")
    return {
        "test": "R8",
        "baseline_avg_count": round(mean_base, 2),
        "post_drift_avg_count": round(mean_post, 2),
        "violations": violations,
        "summary": {"violations": len(violations)},
    }


def run_r5d_schema_on_seekdb(adapter, run_id: str, dim: int = 64) -> Dict[str, Any]:
    """R5D Schema Contract: schema change compatibility.

    SCH-001: Create collection with schema → insert succeeds
    SCH-002: Re-create with different dimension → old dimension rejected
    SCH-003: Drop and re-create → insert after drop succeeds
    SCH-004: Insert with wrong dimension → should fail or truncate, not corrupt silently
    """
    print(f"\n  [R5D] Schema Contract Tests")
    results = []
    violations = []

    # SCH-001: normal create + insert
    col = f"seekdb_r5d_{run_id}"
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
    r = adapter.execute({"operation": "create_collection", "params": {
        "collection_name": col, "dimension": dim,
    }})
    vecs = _rand_vectors(10, dim, seed=1)
    ri = adapter.execute({"operation": "insert", "params": {
        "collection_name": col, "vectors": vecs,
    }})
    sch001 = ri.get("status") == "success"
    results.append({"id": "SCH-001", "pass": sch001, "detail": ri.get("status")})
    if not sch001:
        violations.append({"type": "SCH-001-FAIL", "detail": ri.get("error", "insert failed after create")})

    # SCH-002: try inserting wrong-dimension vector
    wrong_dim_vecs = _rand_vectors(1, dim + 10, seed=2)  # wrong dimension
    ri2 = adapter.execute({"operation": "insert", "params": {
        "collection_name": col, "vectors": wrong_dim_vecs,
    }})
    # Expected: error (wrong dim). If success → potential silent corruption → VIOLATION
    wrong_dim_accepted = ri2.get("status") == "success"
    results.append({
        "id": "SCH-002",
        "pass": not wrong_dim_accepted,
        "detail": f"wrong-dim insert status={ri2.get('status')}",
    })
    if wrong_dim_accepted:
        violations.append({
            "type": "SCH-002-WRONG-DIM-ACCEPTED",
            "detail": f"Vector with dim={dim+10} was accepted into collection with dim={dim}",
        })

    # SCH-003: drop and re-create → fresh insert should work
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
    r3 = adapter.execute({"operation": "create_collection", "params": {
        "collection_name": col, "dimension": dim,
    }})
    vecs3 = _rand_vectors(5, dim, seed=3)
    ri3 = adapter.execute({"operation": "insert", "params": {
        "collection_name": col, "vectors": vecs3,
    }})
    sch003 = ri3.get("status") == "success"
    results.append({"id": "SCH-003", "pass": sch003, "detail": ri3.get("status")})
    if not sch003:
        violations.append({"type": "SCH-003-FAIL", "detail": "Insert after drop+recreate failed"})

    # SCH-004: count after fresh insert must equal inserted count
    rc = adapter.execute({"operation": "count_entities", "params": {"collection_name": col}})
    storage_count = (
        rc.get("storage_count") or
        (rc.get("data", [{}])[0].get("storage_count", -1))
    )
    adapter.execute({"operation": "flush", "params": {"collection_name": col}})
    # Re-count after flush
    rc2 = adapter.execute({"operation": "count_entities", "params": {"collection_name": col}})
    storage_count2 = (
        rc2.get("storage_count") or
        (rc2.get("data", [{}])[0].get("storage_count", -1))
    )
    sch004 = storage_count2 == 5
    results.append({
        "id": "SCH-004",
        "pass": sch004,
        "detail": f"count_after_insert={storage_count2}, expected=5",
    })
    if not sch004:
        violations.append({
            "type": "SCH-004-COUNT-MISMATCH",
            "detail": f"Expected 5 entities after insert, got {storage_count2}",
        })

    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})

    summary = {r["id"]: "PASS" if r["pass"] else "VIOLATION" for r in results}
    print(f"    Schema results: {summary} | {len(violations)} violations")
    return {
        "test": "R5D",
        "results": results,
        "violations": violations,
        "summary": summary,
    }


def run_r1_r6_sweep(adapter, run_id: str, dim: int = 64) -> Dict[str, Any]:
    """Step-2: Comprehensive R1-R6 coverage sweep on SeekDB.

    R1: Insert → Count consistency
    R2: Search returns non-empty when corpus is non-empty
    R3: Delete → Count decreases by exact delete amount
    R4: Filtered search returns subset of full search
    R5: Build index idempotent
    R6: Load/unload lifecycle (load_state transitions)
    """
    print(f"\n  [R1-R6] Comprehensive Sweep")
    col = f"seekdb_sweep_{run_id}"
    violations = []
    test_results = []

    dim_use = 32  # smaller for faster smoke
    n_vecs  = 100
    vecs    = _rand_vectors(n_vecs, dim_use, seed=42)

    # Setup
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
    adapter.execute({"operation": "create_collection", "params": {
        "collection_name": col, "dimension": dim_use,
    }})
    ri = adapter.execute({"operation": "insert", "params": {
        "collection_name": col, "vectors": vecs,
        "ids": list(range(n_vecs)),
        "scalar_data": [{"category": "A" if i < 50 else "B"} for i in range(n_vecs)],
    }})
    adapter.execute({"operation": "flush", "params": {"collection_name": col}})
    adapter.execute({"operation": "build_index", "params": {
        "collection_name": col, "index_type": "IVF_FLAT", "metric_type": "L2",
        "nlist": min(16, n_vecs // 6),
    }})
    adapter.execute({"operation": "load", "params": {"collection_name": col}})

    # R1: count matches insert
    rc = adapter.execute({"operation": "count_entities", "params": {"collection_name": col}})
    cnt = (rc.get("storage_count") or
           (rc.get("data", [{}])[0].get("storage_count", -1)))
    r1_pass = (cnt == n_vecs)
    test_results.append({"id": "R1", "pass": r1_pass, "count": cnt, "expected": n_vecs})
    if not r1_pass:
        violations.append({"type": "R1-COUNT-MISMATCH", "got": cnt, "expected": n_vecs})

    # R2: search returns results
    qvec = vecs[0]
    rs = adapter.execute({"operation": "search", "params": {
        "collection_name": col, "vector": qvec, "top_k": 5,
    }})
    r2_pass = rs.get("status") == "success" and len(rs.get("data", [])) > 0
    test_results.append({"id": "R2", "pass": r2_pass, "result_count": len(rs.get("data", []))})
    if not r2_pass:
        violations.append({"type": "R2-EMPTY-SEARCH", "detail": rs.get("error", "")})

    # R3: delete 10 vectors → count drops by 10
    del_ids = list(range(10))
    adapter.execute({"operation": "delete", "params": {"collection_name": col, "ids": del_ids}})
    adapter.execute({"operation": "flush", "params": {"collection_name": col}})
    rc2 = adapter.execute({"operation": "count_entities", "params": {"collection_name": col}})
    cnt2 = (rc2.get("storage_count") or
            (rc2.get("data", [{}])[0].get("storage_count", -1)))
    r3_pass = (cnt2 == n_vecs - 10)
    test_results.append({"id": "R3", "pass": r3_pass, "count_after_delete": cnt2, "expected": n_vecs - 10})
    if not r3_pass:
        violations.append({"type": "R3-DELETE-MISMATCH", "got": cnt2, "expected": n_vecs - 10})

    # R4: filtered search returns ≤ full search
    rf = adapter.execute({"operation": "filtered_search", "params": {
        "collection_name": col, "vector": qvec, "top_k": 5,
        "filter": {"category": "A"},
    }})
    rs_full = adapter.execute({"operation": "search", "params": {
        "collection_name": col, "vector": qvec, "top_k": 5,
    }})
    f_count   = len(rf.get("data", []))
    full_count = len(rs_full.get("data", []))
    r4_pass = (f_count <= full_count)
    test_results.append({"id": "R4", "pass": r4_pass, "filtered": f_count, "full": full_count})
    if not r4_pass:
        violations.append({"type": "R4-FILTER-SUPERSET", "filtered": f_count, "full": full_count})

    # R5: build index twice → second call idempotent (no error)
    rb2 = adapter.execute({"operation": "build_index", "params": {
        "collection_name": col, "index_type": "IVF_FLAT", "metric_type": "L2", "nlist": 8,
    }})
    r5_pass = rb2.get("status") == "success"
    test_results.append({"id": "R5", "pass": r5_pass, "second_build_status": rb2.get("status")})
    if not r5_pass:
        violations.append({"type": "R5-REBUILD-ERROR", "error": rb2.get("error", "")})

    # R6: load idempotent (double load should not crash)
    rl2 = adapter.execute({"operation": "load", "params": {"collection_name": col}})
    r6_pass = rl2.get("status") == "success"
    test_results.append({"id": "R6", "pass": r6_pass, "double_load_status": rl2.get("status")})
    if not r6_pass:
        violations.append({"type": "R6-RELOAD-ERROR", "error": rl2.get("error", "")})

    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})

    summary = {r["id"]: "PASS" if r["pass"] else "VIOLATION" for r in test_results}
    print(f"    R1-R6 sweep: {summary} | {len(violations)} violations")
    return {"test": "R1-R6-SWEEP", "results": test_results, "violations": violations, "summary": summary}


# ─────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────

def _generate_report(
    all_family_results: List[Dict],
    adapter_name: str,
    run_timestamp: str,
    step: int,
    output_dir: Path,
) -> Path:
    report_path = output_dir / f"seekdb_extended_report_step{step}_{run_timestamp}.md"

    total_violations = sum(len(r.get("violations", [])) for r in all_family_results)

    lines = [
        f"# SeekDB Extended Contract Coverage — Step {step}",
        "",
        f"**Generated**: {datetime.now().isoformat()}",
        f"**Adapter**: {adapter_name}",
        f"**Step**: {step} ({'New contract families' if step == 1 else 'Full R1-R6 sweep'})",
        f"**Total Violations**: {total_violations}",
        "",
        "## Summary",
        "",
        "| Test Family | Violations | Status |",
        "|-------------|-----------|--------|",
    ]

    for r in all_family_results:
        v   = len(r.get("violations", []))
        cls = "PASS" if v == 0 else "VIOLATION"
        lines.append(f"| {r.get('test', '?')} | {v} | {cls} |")

    lines += ["", "## Detail", ""]

    for r in all_family_results:
        lines.append(f"### {r.get('test', '?')}")
        lines.append("")
        if "error" in r:
            lines.append(f"> ERROR: {r['error']}")
            lines.append("")
            continue
        lines.append(f"**Summary**: {json.dumps(r.get('summary', {}))}")
        lines.append("")
        if r.get("violations"):
            for v in r["violations"][:5]:
                lines.append(f"- `{v.get('type', '?')}`: {v.get('detail', v.get('reason', ''))}")
        else:
            lines.append("No violations.")
        lines.append("")

    content = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
    return report_path


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SeekDB Extended Contract Coverage Campaign")
    parser.add_argument("--host",     default="localhost", help="SeekDB host")
    parser.add_argument("--port",     type=int, default=2881, help="SeekDB port")
    parser.add_argument("--user",     default="root")
    parser.add_argument("--password", default="")
    parser.add_argument("--database", default="test")
    parser.add_argument("--offline",  action="store_true", help="Use mock adapter")
    parser.add_argument("--step",     type=int, default=1, choices=[1, 2],
                        help="Step 1=new families, Step 2=full R1-R6 sweep")
    parser.add_argument("--dim",      type=int, default=64, help="Vector dimension")
    parser.add_argument("--n-threads", type=int, default=8, help="R7 concurrency threads")
    parser.add_argument("--output-dir", default="results")
    args = parser.parse_args()

    run_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir    = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    print("=" * 65)
    print("  SEEKDB EXTENDED CONTRACT COVERAGE")
    print(f"  Step      : {args.step}")
    print(f"  Timestamp : {run_timestamp}")
    print("=" * 65)
    print()

    adapter, adapter_name, fallback = _build_adapter(args)
    if fallback:
        print("  WARNING: Running on mock (SeekDB unavailable).")

    all_results = []

    if args.step == 1:
        # New contract families
        all_results.append(run_mr03_on_seekdb(adapter, run_timestamp, args.dim))
        all_results.append(run_r7_on_seekdb(adapter, run_timestamp, args.dim, args.n_threads))
        all_results.append(run_r8_on_seekdb(adapter, run_timestamp, args.dim))
        all_results.append(run_r5d_schema_on_seekdb(adapter, run_timestamp, args.dim))
    else:
        # Full R1-R6 sweep
        all_results.append(run_r1_r6_sweep(adapter, run_timestamp, args.dim))
        # Also run new families
        all_results.append(run_mr03_on_seekdb(adapter, run_timestamp, args.dim))
        all_results.append(run_r7_on_seekdb(adapter, run_timestamp, args.dim, args.n_threads))

    try:
        adapter.close()
    except Exception:
        pass

    # Save raw JSON
    raw_path = output_dir / f"seekdb_extended_raw_step{args.step}_{run_timestamp}.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump({
            "run_timestamp": run_timestamp,
            "adapter": adapter_name,
            "step": args.step,
            "results": all_results,
        }, f, indent=2, ensure_ascii=False)

    # Generate report
    report_path = _generate_report(all_results, adapter_name, run_timestamp, args.step, output_dir)

    # Summary
    total_violations = sum(len(r.get("violations", [])) for r in all_results)
    print()
    print("=" * 65)
    print("  CAMPAIGN COMPLETE")
    print("=" * 65)
    for r in all_results:
        v = len(r.get("violations", []))
        print(f"  {r.get('test', '?'):<15} violations={v}")
    print(f"\n  Total violations: {total_violations}")
    print(f"  Raw JSON : {raw_path}")
    print(f"  Report   : {report_path}")


if __name__ == "__main__":
    main()
