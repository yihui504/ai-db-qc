"""Run R8 Data Drift Protocol on SeekDB.

Tests DRIFT-001~004 contract family (incremental insertion recall degradation)
against SeekDB and optionally produces a cross-database comparison against a
Milvus baseline.

Architecture note
─────────────────
SeekDB's SQL interface uses `l2_distance()` for ANN search.  The ground-truth
oracle is computed in-Python by brute-force cosine/L2 on the same vectors
(no FLAT index required — we never INSERT ground-truth; we compute it locally).
This avoids the Milvus FLAT dependency described in the plan.

Contracts
──────────
DRIFT-001  Baseline recall@k ≥ 0.99 on fresh collection (N0 vectors)
DRIFT-002  Recall remains ≥ baseline×0.95 after incremental inserts
           (N0 → 2×N0 → 4×N0); logs degradation curve
DRIFT-003  (N/A on SeekDB — no manual rebuild; logged as ARCHITECTURAL_NA)
DRIFT-004  Delete 50% of vectors, re-insert → count exact + recall not degraded

Usage (online):
    python scripts/run_r8_seekdb.py \\
        --host localhost --port 2881 \\
        --n-base 500 --n-drift 500 --n-probes 10 --dim 64 \\
        --output-dir results/r8_seekdb

Usage (offline / mock):
    python scripts/run_r8_seekdb.py --offline --dim 16 --n-base 60 --output-dir results/smoke
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_vectors(n: int, dim: int, seed: int = 0) -> List[List[float]]:
    rng = random.Random(seed)
    vecs: List[List[float]] = []
    for _ in range(n):
        v = [rng.gauss(0, 1) for _ in range(dim)]
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        vecs.append([x / norm for x in v])
    return vecs


def l2_dist(a: List[float], b: List[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def brute_force_topk(corpus: List[Tuple[int, List[float]]],
                     query: List[float], k: int) -> List[int]:
    """Return top-k ids by L2 from corpus (list of (id, vec))."""
    dists = [(dist_id, l2_dist(vec, query)) for dist_id, vec in corpus]
    dists.sort(key=lambda x: x[1])
    return [x[0] for x in dists[:k]]


def recall_at_k(predicted: List[int], ground_truth: List[int]) -> float:
    gt_set = set(ground_truth)
    hits = sum(1 for p in predicted if p in gt_set)
    return hits / len(gt_set) if gt_set else 1.0


# ── SeekDB thin client ────────────────────────────────────────────────────────

class SeekDBDriftClient:
    """Minimal SeekDB client for drift testing (raw pymysql)."""

    def __init__(self, host: str, port: int, user: str, password: str,
                 database: str, dim: int):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.dim = dim
        self._conn: Optional[Any] = None

    def connect(self) -> bool:
        try:
            import pymysql
            self._conn = pymysql.connect(
                host=self.host, port=self.port,
                user=self.user, password=self.password,
                database=self.database, charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=5,
            )
            return True
        except Exception as e:
            print(f"  SeekDB connect error: {e}")
            return False

    def _cursor(self):
        import pymysql
        if self._conn is None or not self._conn.open:
            self._conn = pymysql.connect(
                host=self.host, port=self.port,
                user=self.user, password=self.password,
                database=self.database, charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
        return self._conn.cursor()

    def create_table(self, name: str) -> None:
        cur = self._cursor()
        cur.execute(f"DROP TABLE IF EXISTS {name}")
        cur.execute(
            f"CREATE TABLE {name} "
            f"(id INT PRIMARY KEY, embedding VECTOR({self.dim}))"
        )
        self._conn.commit()
        cur.close()

    def insert(self, name: str, vecs: List[List[float]],
               id_offset: int = 0) -> int:
        cur = self._cursor()
        for i, vec in enumerate(vecs):
            literal = "[" + ", ".join(f"{v:.6f}" for v in vec) + "]"
            cur.execute(
                f"INSERT INTO {name} (id, embedding) VALUES (%s, %s)",
                (id_offset + i, literal),
            )
        self._conn.commit()
        cur.close()
        return len(vecs)

    def delete_ids(self, name: str, ids: List[int]) -> int:
        cur = self._cursor()
        placeholders = ",".join(["%s"] * len(ids))
        cur.execute(f"DELETE FROM {name} WHERE id IN ({placeholders})", ids)
        self._conn.commit()
        deleted = cur.rowcount
        cur.close()
        return deleted

    def count(self, name: str) -> int:
        cur = self._cursor()
        cur.execute(f"SELECT COUNT(*) AS cnt FROM {name}")
        row = cur.fetchone()
        cur.close()
        return int(row["cnt"]) if row else 0

    def search(self, name: str, query: List[float], top_k: int) -> List[int]:
        cur = self._cursor()
        literal = "[" + ", ".join(f"{v:.6f}" for v in query) + "]"
        cur.execute(
            f"SELECT id FROM {name} ORDER BY l2_distance(embedding, %s) LIMIT %s",
            (literal, top_k),
        )
        rows = cur.fetchall()
        cur.close()
        return [r["id"] for r in rows]

    def drop_table(self, name: str) -> None:
        try:
            cur = self._cursor()
            cur.execute(f"DROP TABLE IF EXISTS {name}")
            self._conn.commit()
            cur.close()
        except Exception:
            pass


# ── In-memory mock (offline mode) ─────────────────────────────────────────────

class MockDriftClient:
    """Pure-Python in-memory mock for offline smoke testing."""

    def __init__(self, dim: int):
        self.dim = dim
        self._tables: Dict[str, List[Tuple[int, List[float]]]] = {}

    def connect(self) -> bool:
        return True

    def create_table(self, name: str) -> None:
        self._tables[name] = []

    def insert(self, name: str, vecs: List[List[float]],
               id_offset: int = 0) -> int:
        tbl = self._tables.setdefault(name, [])
        for i, vec in enumerate(vecs):
            tbl.append((id_offset + i, vec))
        return len(vecs)

    def delete_ids(self, name: str, ids: List[int]) -> int:
        id_set = set(ids)
        before = len(self._tables.get(name, []))
        self._tables[name] = [
            (rid, vec) for rid, vec in self._tables.get(name, [])
            if rid not in id_set
        ]
        return before - len(self._tables[name])

    def count(self, name: str) -> int:
        return len(self._tables.get(name, []))

    def search(self, name: str, query: List[float], top_k: int) -> List[int]:
        corpus = self._tables.get(name, [])
        return brute_force_topk(corpus, query, top_k)

    def drop_table(self, name: str) -> None:
        self._tables.pop(name, None)


# ── Contract runners ──────────────────────────────────────────────────────────

def run_drift001(client, col: str, n_base: int, n_probes: int,
                 dim: int, top_k: int = 10) -> Dict[str, Any]:
    """DRIFT-001: Baseline recall >= 0.99 on fresh collection."""
    print(f"\n  [DRIFT-001] Baseline Recall (n={n_base}, probes={n_probes})")
    vecs = make_vectors(n_base, dim, seed=1001)
    corpus: List[Tuple[int, List[float]]] = [(i, v) for i, v in enumerate(vecs)]

    client.create_table(col)
    client.insert(col, vecs, id_offset=0)

    query_vecs = make_vectors(n_probes, dim, seed=9999)
    recalls: List[float] = []
    for q in query_vecs:
        gt = brute_force_topk(corpus, q, top_k)
        predicted = client.search(col, q, top_k)
        recalls.append(recall_at_k(predicted, gt))

    avg_recall = sum(recalls) / len(recalls) if recalls else 0.0
    passed = avg_recall >= 0.99
    print(f"    avg_recall={avg_recall:.4f}  {'PASS' if passed else 'VIOLATION'}")
    return {
        "contract": "DRIFT-001",
        "n_base": n_base,
        "n_probes": n_probes,
        "avg_recall": round(avg_recall, 4),
        "min_recall": round(min(recalls), 4) if recalls else 0,
        "threshold": 0.99,
        "classification": "PASS" if passed else "VIOLATION",
        "violation_detail": None if passed else f"avg_recall={avg_recall:.4f} < 0.99",
    }


def run_drift002(client, col: str, n_base: int, n_drift: int, n_probes: int,
                 dim: int, top_k: int = 10) -> Dict[str, Any]:
    """DRIFT-002: Recall remains >= baseline*0.95 after incremental inserts."""
    print(f"\n  [DRIFT-002] Incremental Degradation (drift={n_drift} × 2 batches)")
    base_vecs = make_vectors(n_base, dim, seed=1001)
    corpus: List[Tuple[int, List[float]]] = [(i, v) for i, v in enumerate(base_vecs)]
    # table should already have base_vecs from DRIFT-001
    # if this is run standalone, re-create
    if client.count(col) == 0:
        client.create_table(col)
        client.insert(col, base_vecs, id_offset=0)

    query_vecs = make_vectors(n_probes, dim, seed=8888)

    def _avg_recall(extra_corpus) -> float:
        rs = []
        for q in query_vecs:
            gt = brute_force_topk(corpus + extra_corpus, q, top_k)
            predicted = client.search(col, q, top_k)
            rs.append(recall_at_k(predicted, gt))
        return sum(rs) / len(rs) if rs else 0.0

    # baseline recall
    baseline_recall = _avg_recall([])
    curve: List[Dict] = [{"total_vectors": n_base, "avg_recall": round(baseline_recall, 4)}]
    print(f"    baseline ({n_base} vecs): recall={baseline_recall:.4f}")

    violations: List[str] = []
    next_id = n_base
    for batch_i in range(2):
        batch_vecs = make_vectors(n_drift, dim, seed=2000 + batch_i * 100)
        client.insert(col, batch_vecs, id_offset=next_id)
        new_entries = [(next_id + j, v) for j, v in enumerate(batch_vecs)]
        corpus.extend(new_entries)
        next_id += n_drift
        current_total = n_base + (batch_i + 1) * n_drift
        recall_now = _avg_recall([])
        curve.append({"total_vectors": current_total, "avg_recall": round(recall_now, 4)})
        print(f"    after batch {batch_i + 1} ({current_total} vecs): recall={recall_now:.4f}")
        if recall_now < baseline_recall * 0.95:
            violations.append(
                f"Batch {batch_i + 1}: recall dropped to {recall_now:.4f} "
                f"(< {baseline_recall * 0.95:.4f})"
            )

    passed = not violations
    print(f"    {'PASS' if passed else 'VIOLATION'}")
    return {
        "contract": "DRIFT-002",
        "baseline_recall": round(baseline_recall, 4),
        "threshold_multiplier": 0.95,
        "degradation_curve": curve,
        "violations": violations,
        "classification": "PASS" if passed else "VIOLATION",
    }


def run_drift003_na() -> Dict[str, Any]:
    """DRIFT-003: Rebuild recovery — N/A on SeekDB (no manual index rebuild)."""
    print(f"\n  [DRIFT-003] Rebuild Recovery — ARCHITECTURAL_NA on SeekDB")
    return {
        "contract": "DRIFT-003",
        "classification": "ARCHITECTURAL_NA",
        "reason": (
            "SeekDB manages indexing automatically; manual index rebuild "
            "via build_index/load is a no-op. DRIFT-003 is not applicable."
        ),
    }


def run_drift004(client, col: str, n_base: int, n_drift: int, n_probes: int,
                 dim: int, top_k: int = 10) -> Dict[str, Any]:
    """DRIFT-004: Delete 50% and re-insert; count exact + recall not degraded."""
    print(f"\n  [DRIFT-004] Delete-Reinsert (50% delete + reinsert)")
    current_count = client.count(col)
    if current_count == 0:
        base_vecs = make_vectors(n_base, dim, seed=1001)
        client.create_table(col)
        client.insert(col, base_vecs, id_offset=0)
        current_count = n_base

    ids_to_delete = list(range(0, current_count // 2))
    print(f"    current count={current_count}, deleting {len(ids_to_delete)} ids")
    deleted = client.delete_ids(col, ids_to_delete)
    count_after_delete = client.count(col)
    expected_after_delete = current_count - len(ids_to_delete)

    # Re-insert deleted vectors
    reinsert_vecs = make_vectors(len(ids_to_delete), dim, seed=5555)
    client.insert(col, reinsert_vecs, id_offset=max(ids_to_delete) + 1000)
    count_final = client.count(col)
    expected_final = count_after_delete + len(ids_to_delete)

    violations: List[str] = []
    if abs(count_final - expected_final) > 0:
        violations.append(
            f"Count mismatch after reinsert: expected {expected_final}, got {count_final}"
        )

    # Build updated corpus for oracle
    surviving = list(range(current_count // 2, current_count))
    new_ids = [max(ids_to_delete) + 1000 + j for j in range(len(ids_to_delete))]
    all_ids_in_db = surviving + new_ids
    corpus_vecs = make_vectors(current_count, dim, seed=1001)[current_count // 2:]  # surviving
    corpus_vecs += reinsert_vecs
    corpus = list(zip(all_ids_in_db, corpus_vecs))

    query_vecs = make_vectors(n_probes, dim, seed=7777)
    recalls: List[float] = []
    for q in query_vecs:
        gt = brute_force_topk(corpus, q, top_k)
        predicted = client.search(col, q, top_k)
        recalls.append(recall_at_k(predicted, gt))

    avg_recall = sum(recalls) / len(recalls) if recalls else 0.0
    if avg_recall < 0.95:
        violations.append(f"Post-reinsert recall={avg_recall:.4f} < 0.95")

    passed = not violations
    print(f"    count_final={count_final}, recall={avg_recall:.4f}  {'PASS' if passed else 'VIOLATION'}")
    return {
        "contract": "DRIFT-004",
        "deleted_count": deleted,
        "count_after_delete": count_after_delete,
        "count_final": count_final,
        "expected_final": expected_final,
        "avg_recall_post_reinsert": round(avg_recall, 4),
        "violations": violations,
        "classification": "PASS" if passed else "VIOLATION",
    }


# ── Milvus baseline reference ─────────────────────────────────────────────────

MILVUS_BASELINE_R8: Dict[str, Any] = {
    "DRIFT-001": {"avg_recall": 1.0, "classification": "PASS"},
    "DRIFT-002": {"baseline_recall": 1.0, "classification": "PASS"},
    "DRIFT-003": {"classification": "PASS"},
    "DRIFT-004": {"avg_recall_post_reinsert": 1.0, "classification": "PASS"},
}


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="R8 Data Drift Testing on SeekDB — DRIFT-001~004"
    )
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=2881)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default="")
    parser.add_argument("--database", default="test")
    parser.add_argument("--dim", type=int, default=64)
    parser.add_argument("--n-base", type=int, default=500)
    parser.add_argument("--n-drift", type=int, default=500)
    parser.add_argument("--n-probes", type=int, default=10)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--offline", action="store_true",
                        help="Use in-memory mock instead of SeekDB")
    parser.add_argument("--output-dir", default="results/r8_seekdb")
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"r8-seekdb-{ts}"
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  R8 Data Drift Campaign — SeekDB")
    print(f"  Run ID : {run_id}")
    print(f"  Mode   : {'OFFLINE (mock)' if args.offline else f'ONLINE {args.host}:{args.port}'}")
    print(f"  dim={args.dim}  n_base={args.n_base}  n_drift={args.n_drift}  probes={args.n_probes}")
    print(f"{'='*60}")

    if args.offline:
        client = MockDriftClient(dim=args.dim)
        client.connect()
    else:
        client = SeekDBDriftClient(
            host=args.host, port=args.port,
            user=args.user, password=args.password,
            database=args.database, dim=args.dim,
        )
        if not client.connect():
            print("  Cannot connect to SeekDB. Use --offline for smoke testing.")
            sys.exit(1)
        print(f"  SeekDB connected OK\n")

    col = f"r8drift_{ts.replace('-', '_')}"
    results: Dict[str, Any] = {}

    try:
        r1 = run_drift001(client, col, args.n_base, args.n_probes,
                          args.dim, args.top_k)
        results["DRIFT-001"] = r1

        r2 = run_drift002(client, col, args.n_base, args.n_drift,
                          args.n_probes, args.dim, args.top_k)
        results["DRIFT-002"] = r2

        results["DRIFT-003"] = run_drift003_na()

        r4 = run_drift004(client, col, args.n_base, args.n_drift,
                          args.n_probes, args.dim, args.top_k)
        results["DRIFT-004"] = r4

    finally:
        client.drop_table(col)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  R8 SEEKDB CAMPAIGN SUMMARY")
    print(f"{'='*60}")
    for cid, r in results.items():
        cls = r.get("classification", "?")
        detail = ""
        if cls == "VIOLATION":
            detail = " | " + "; ".join(r.get("violations", r.get("violation_detail", "")))
        print(f"  {cid}: {cls}{detail}")

    print(f"\n  SEEKDB vs MILVUS COMPARISON")
    print(f"  {'Contract':<14} {'SeekDB':>8} {'Milvus':>8} {'Match?':>8}")
    print(f"  {'-'*42}")
    for cid in ["DRIFT-001", "DRIFT-002", "DRIFT-004"]:
        s_cls = results.get(cid, {}).get("classification", "?")
        m_cls = MILVUS_BASELINE_R8.get(cid, {}).get("classification", "?")
        match = "SAME" if s_cls == m_cls else "DIFF"
        print(f"  {cid:<14} {s_cls:>8} {m_cls:>8} {match:>8}")
    print(f"  DRIFT-003       ARCH_NA     PASS       DIFF (expected)")
    print(f"{'='*60}\n")

    # ── Save ──────────────────────────────────────────────────────────────────
    report = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "mode": "offline" if args.offline else "online",
        "target": "seekdb_mock" if args.offline else "seekdb",
        "config": {
            "host": args.host, "port": args.port,
            "dim": args.dim, "n_base": args.n_base,
            "n_drift": args.n_drift, "n_probes": args.n_probes,
        },
        "milvus_baseline": MILVUS_BASELINE_R8,
        "results": results,
    }

    json_path = out_dir / f"{run_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    # Markdown
    md_lines = [
        "# R8 Data Drift — SeekDB Report",
        "",
        f"**Run ID**: {run_id}  ",
        f"**Mode**: {'Offline (mock)' if args.offline else f'SeekDB {args.host}:{args.port}'}  ",
        f"**Timestamp**: {report['timestamp']}",
        "",
        "## Results",
        "",
        "| Contract | SeekDB | Milvus | Match? |",
        "|----------|--------|--------|--------|",
    ]
    for cid in ["DRIFT-001", "DRIFT-002", "DRIFT-004"]:
        s_cls = results.get(cid, {}).get("classification", "?")
        m_cls = MILVUS_BASELINE_R8.get(cid, {}).get("classification", "?")
        match = "SAME" if s_cls == m_cls else "DIFF"
        md_lines.append(f"| {cid} | {s_cls} | {m_cls} | {match} |")
    md_lines.append(
        "| DRIFT-003 | ARCHITECTURAL_NA | PASS | DIFF (expected — SeekDB no-op rebuild) |"
    )
    md_lines += [
        "",
        "## SeekDB Architectural Notes",
        "",
        "- DRIFT-003 (Rebuild Recovery) is ARCHITECTURAL_NA: SeekDB auto-manages "
        "indexes and does not expose manual rebuild.",
        "- Ground-truth for recall computation is brute-force in-Python L2; "
        "no FLAT index needed.",
        "",
        f"*Saved: {json_path}*",
    ]

    md_path = out_dir / f"{run_id}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"  JSON : {json_path}")
    print(f"  MD   : {md_path}")


if __name__ == "__main__":
    main()
