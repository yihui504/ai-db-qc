"""Run MR-03 Semantic Metamorphic Testing on SeekDB.

Mirrors run_semantic_extended.py but targets SeekDB via SQL adapter.
Compares violation rates against the Milvus baseline from
run_semantic_extended.py to produce a cross-database differential report.

Architecture note
─────────────────
SeekDB uses a MySQL-compatible SQL interface with `l2_distance()`.
Embedding insertion: each text pair's embedding is stored as a row;
  queries use `ORDER BY l2_distance(embedding, '[...]') LIMIT k`.
Since SeekDB's `build_index` / `load` are no-ops, we skip them.
Contracts tested: MR-01 (positive recall), MR-03 (hard-negative rejection),
  MR-04 (unrelated rejection).

Usage (online):
    python scripts/run_semantic_seekdb.py \\
        --host localhost --port 2881 \\
        --domains finance medical legal code \\
        --n-positives 5 --n-negatives 3 --n-hard-negatives 6 \\
        --output-dir results/semantic_seekdb

Usage (offline embedding only):
    python scripts/run_semantic_seekdb.py \\
        --offline \\
        --domains legal code --output-dir results/smoke
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_db_qa.semantic_datagen import DOMAIN_TEMPLATES
from adapters.mock import MockAdapter

# ── Optional heavy imports (embeddings) ──────────────────────────────────────

try:
    from sentence_transformers import SentenceTransformer
    _HAS_ST = True
except ImportError:
    _HAS_ST = False


# ── Constants ─────────────────────────────────────────────────────────────────

SEEKDB_DIM = 384  # all-MiniLM-L6-v2 output dimension
TOP_K = 10
COSINE_THRESHOLD_HARD_NEG = 0.85   # flag if hard-negative scores above this

_VIOLATION_TYPES = {
    "MR-01": "positive_recall_failure",
    "MR-03": "hard_negative_not_rejected",
    "MR-04": "unrelated_not_rejected",
}


# ── Cosine similarity ─────────────────────────────────────────────────────────

def cosine_sim(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ── Embedding provider ────────────────────────────────────────────────────────

class EmbeddingProvider:
    """Wraps sentence-transformers or falls back to random vectors."""

    def __init__(self, offline: bool = False):
        self.offline = offline
        self._model: Optional[Any] = None
        if not offline and _HAS_ST:
            print("  Loading sentence-transformers (all-MiniLM-L6-v2)...")
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            print("  Model loaded.")
        elif not offline:
            print("  WARNING: sentence-transformers not installed; falling back to random vectors.")

    def embed(self, texts: List[str]) -> List[List[float]]:
        if self._model is not None:
            return self._model.encode(texts, normalize_embeddings=True).tolist()
        # Deterministic random fallback (seeded on text hash)
        out = []
        for t in texts:
            rng = random.Random(hash(t) & 0xFFFFFFFF)
            v = [rng.gauss(0, 1) for _ in range(SEEKDB_DIM)]
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / norm for x in v])
        return out


# ── SeekDB thin client (pure SQL via pymysql, no adapter overhead) ─────────────

def _make_seekdb_connection(host: str, port: int, user: str, password: str,
                            database: str) -> Any:
    try:
        import pymysql
        conn = pymysql.connect(
            host=host, port=port, user=user, password=password,
            database=database, charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
        )
        return conn
    except Exception as e:
        raise RuntimeError(f"Cannot connect to SeekDB at {host}:{port} — {e}")


def _vec_literal(vec: List[float]) -> str:
    return "[" + ", ".join(f"{v:.6f}" for v in vec) + "]"


class SeekDBSemanticRunner:
    """Run MR-01/03/04 tests directly against SeekDB via SQL."""

    def __init__(self, host: str, port: int, user: str = "root",
                 password: str = "", database: str = "test",
                 dim: int = SEEKDB_DIM):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.dim = dim
        self._conn: Optional[Any] = None

    def connect(self) -> bool:
        try:
            self._conn = _make_seekdb_connection(
                self.host, self.port, self.user, self.password, self.database
            )
            return True
        except Exception as e:
            print(f"  SeekDB connection failed: {e}")
            return False

    def _cursor(self):
        if self._conn is None or not self._conn.open:
            self._conn = _make_seekdb_connection(
                self.host, self.port, self.user, self.password, self.database
            )
        return self._conn.cursor()

    def _create_table(self, name: str) -> None:
        cur = self._cursor()
        cur.execute(f"DROP TABLE IF EXISTS {name}")
        cur.execute(
            f"CREATE TABLE {name} "
            f"(id INT PRIMARY KEY, embedding VECTOR({self.dim}))"
        )
        self._conn.commit()
        cur.close()

    def _insert_vectors(self, name: str, vecs: List[List[float]],
                        start_id: int = 0) -> None:
        cur = self._cursor()
        for i, vec in enumerate(vecs):
            cur.execute(
                f"INSERT INTO {name} (id, embedding) VALUES (%s, %s)",
                (start_id + i, _vec_literal(vec)),
            )
        self._conn.commit()
        cur.close()

    def _search(self, name: str, query_vec: List[float], top_k: int) -> List[Dict]:
        cur = self._cursor()
        cur.execute(
            f"SELECT id, l2_distance(embedding, %s) AS dist "
            f"FROM {name} ORDER BY dist LIMIT %s",
            (_vec_literal(query_vec), top_k),
        )
        rows = cur.fetchall()
        cur.close()
        return [{"id": r["id"], "dist": float(r["dist"])} for r in rows]

    def _drop_table(self, name: str) -> None:
        try:
            cur = self._cursor()
            cur.execute(f"DROP TABLE IF EXISTS {name}")
            self._conn.commit()
            cur.close()
        except Exception:
            pass

    def run_pair(
        self,
        domain: str,
        pair_type: str,          # "positive" | "negative" | "hard_negative"
        text_a: str,
        text_b: str,
        label: str,
        emb_a: List[float],
        emb_b: List[float],
        pair_idx: int,
    ) -> Dict[str, Any]:
        """
        Insert text_a embedding into a temp collection; query with text_b.
        Returns a result dict with MR classification.
        """
        col = f"mr_seekdb_{domain}_{pair_type}_{pair_idx}"
        try:
            self._create_table(col)
            self._insert_vectors(col, [emb_a], start_id=0)
            results = self._search(col, emb_b, top_k=TOP_K)
            self._drop_table(col)
        except Exception as e:
            self._drop_table(col)
            return {
                "domain": domain, "pair_type": pair_type, "label": label,
                "status": "error", "error": str(e)[:200],
                "violations": [],
            }

        cos = cosine_sim(emb_a, emb_b)
        returned_ids = [r["id"] for r in results]
        found_target = 0 in returned_ids  # target id=0
        violations: List[str] = []

        if pair_type == "positive":
            # MR-01: positive pair should be recalled
            if not found_target:
                violations.append("MR-01: positive pair not recalled in top-k")
        elif pair_type == "hard_negative":
            # MR-03: hard-negative should NOT be top-1 (cosine > threshold = suspicious)
            if cos >= COSINE_THRESHOLD_HARD_NEG and found_target:
                violations.append(
                    f"MR-03: hard-negative (cos={cos:.3f}) mistakenly top-ranked"
                )
        elif pair_type == "negative":
            # MR-04: unrelated text — cosine should be low; finding it might be OK,
            #        but extremely high cosine is suspicious
            if cos > 0.95:
                violations.append(
                    f"MR-04: unrelated pair has unexpectedly high cosine={cos:.3f}"
                )

        return {
            "domain": domain,
            "pair_type": pair_type,
            "label": label,
            "cosine_sim": round(cos, 4),
            "found_target_in_topk": found_target,
            "top_result_id": returned_ids[0] if returned_ids else None,
            "n_results": len(results),
            "violations": violations,
            "status": "ok",
        }


# ── Offline mock runner (no DB needed) ────────────────────────────────────────

class OfflineSemanticRunner:
    """Compute cosine similarities without a DB; mirrors SeekDBSemanticRunner."""

    def run_pair(
        self, domain: str, pair_type: str, text_a: str, text_b: str,
        label: str, emb_a: List[float], emb_b: List[float], pair_idx: int,
    ) -> Dict[str, Any]:
        cos = cosine_sim(emb_a, emb_b)
        violations: List[str] = []

        if pair_type == "positive" and cos < 0.5:
            violations.append(f"MR-01: positive pair has low cosine={cos:.3f}")
        elif pair_type == "hard_negative" and cos >= COSINE_THRESHOLD_HARD_NEG:
            violations.append(
                f"MR-03: hard-negative similarity={cos:.3f} >= threshold={COSINE_THRESHOLD_HARD_NEG}"
            )
        elif pair_type == "negative" and cos > 0.95:
            violations.append(
                f"MR-04: unrelated pair has unexpectedly high cosine={cos:.3f}"
            )

        return {
            "domain": domain, "pair_type": pair_type, "label": label,
            "cosine_sim": round(cos, 4),
            "violations": violations,
            "status": "ok",
        }


# ── Domain-level campaign ──────────────────────────────────────────────────────

def run_domain_campaign(
    runner,
    domain: str,
    n_positives: int,
    n_negatives: int,
    n_hard_negatives: int,
    emb_provider: EmbeddingProvider,
) -> Dict[str, Any]:
    templates = DOMAIN_TEMPLATES.get(domain)
    if templates is None:
        return {"domain": domain, "error": f"Domain '{domain}' not found in DOMAIN_TEMPLATES"}

    print(f"\n  Domain: {domain.upper()}")

    all_results: List[Dict] = []

    def _run_pairs(key: str, n: int) -> None:
        pool_raw = templates.get(key, [])
        if not pool_raw:
            return
        pool = list(pool_raw)
        random.shuffle(pool)
        pairs = pool[:n]
        texts_a = [p[0] for p in pairs]
        texts_b = [p[1] for p in pairs]
        labels  = [p[2] if len(p) > 2 else "" for p in pairs]
        embs_a = emb_provider.embed(texts_a)
        embs_b = emb_provider.embed(texts_b)
        for idx, (ta, tb, lb, ea, eb) in enumerate(
                zip(texts_a, texts_b, labels, embs_a, embs_b)):
            res = runner.run_pair(domain, key, ta, tb, lb, ea, eb, idx)
            all_results.append(res)
            v = len(res.get("violations", []))
            marker = "V" if v else "."
            print(f"    [{key[:3].upper()}] {marker} cos={res.get('cosine_sim', '?'):.3f} {lb}")

    _run_pairs("positive", n_positives)
    _run_pairs("negative", n_negatives)
    _run_pairs("hard_negative", n_hard_negatives)

    total = len(all_results)
    violations = [r for r in all_results if r.get("violations")]
    by_type: Dict[str, Dict] = {}
    for r in all_results:
        pt = r["pair_type"]
        if pt not in by_type:
            by_type[pt] = {"total": 0, "violations": 0, "cos_sum": 0.0}
        by_type[pt]["total"] += 1
        by_type[pt]["violations"] += 1 if r.get("violations") else 0
        by_type[pt]["cos_sum"] += r.get("cosine_sim", 0.0)

    stats: Dict[str, Any] = {}
    for pt, d in by_type.items():
        n = d["total"] or 1
        stats[pt] = {
            "total": d["total"],
            "violations": d["violations"],
            "violation_rate": round(d["violations"] / n, 3),
            "avg_cosine": round(d["cos_sum"] / n, 4),
        }

    print(f"    --> {len(violations)}/{total} violations  "
          + "  ".join(
              f"{pt}: vr={s['violation_rate']:.1%} cos_avg={s['avg_cosine']:.3f}"
              for pt, s in stats.items()
          ))

    return {
        "domain": domain,
        "total": total,
        "violations": len(violations),
        "violation_rate": round(len(violations) / total, 3) if total else 0,
        "by_type": stats,
        "results": all_results,
    }


# ── Milvus baseline reference (from previous run_semantic_extended results) ────

# Hard-coded approximate baseline from run_semantic_extended smoke results.
# Update these when fresh results are available.
MILVUS_BASELINE: Dict[str, float] = {
    "finance":  0.0,
    "medical":  0.0,
    "legal":    0.05,   # placeholder from smoke (1 MR-04 at high cos)
    "code":     0.10,   # placeholder from smoke (1 MR-04 violation seen)
    "general":  0.0,
}


def _diff_vs_milvus(seekdb_rate: float, milvus_rate: float) -> str:
    delta = seekdb_rate - milvus_rate
    if abs(delta) < 0.02:
        return "~SAME"
    elif delta > 0:
        return f"+{delta:.1%} (SeekDB WORSE)"
    else:
        return f"{delta:.1%} (SeekDB BETTER)"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="MR-03 Semantic Testing on SeekDB — four-domain campaign"
    )
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=2881)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default="")
    parser.add_argument("--database", default="test")
    parser.add_argument("--domains", nargs="+",
                        default=["finance", "medical", "legal", "code"],
                        choices=list(DOMAIN_TEMPLATES.keys()))
    parser.add_argument("--n-positives", type=int, default=5)
    parser.add_argument("--n-negatives", type=int, default=3)
    parser.add_argument("--n-hard-negatives", type=int, default=6)
    parser.add_argument("--offline", action="store_true",
                        help="Skip DB; compute cosine similarities only (no SeekDB needed)")
    parser.add_argument("--output-dir", default="results/semantic_seekdb")
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"semantic-seekdb-{ts}"
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  MR-03 Semantic Campaign — SeekDB")
    print(f"  Run ID : {run_id}")
    print(f"  Mode   : {'OFFLINE (cosine only)' if args.offline else f'ONLINE {args.host}:{args.port}'}")
    print(f"  Domains: {args.domains}")
    print(f"{'='*60}")

    emb_provider = EmbeddingProvider(offline=args.offline)

    if args.offline:
        runner = OfflineSemanticRunner()
    else:
        runner = SeekDBSemanticRunner(
            host=args.host, port=args.port,
            user=args.user, password=args.password,
            database=args.database,
        )
        if not runner.connect():
            print("  Cannot connect to SeekDB. Run with --offline or check connection.")
            sys.exit(1)
        print(f"  SeekDB connected OK\n")

    domain_results: Dict[str, Any] = {}
    for domain in args.domains:
        domain_results[domain] = run_domain_campaign(
            runner=runner,
            domain=domain,
            n_positives=args.n_positives,
            n_negatives=args.n_negatives,
            n_hard_negatives=args.n_hard_negatives,
            emb_provider=emb_provider,
        )

    # ── Cross-domain summary ──────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  SEEKDB vs MILVUS DIFFERENTIAL")
    print(f"{'='*60}")
    print(f"  {'Domain':<12}  {'SeekDB VR':>10}  {'Milvus VR':>10}  Diff")
    print(f"  {'-'*50}")
    for domain in args.domains:
        dr = domain_results.get(domain, {})
        seekdb_vr = dr.get("violation_rate", float("nan"))
        milvus_vr = MILVUS_BASELINE.get(domain, float("nan"))
        diff_str = (
            _diff_vs_milvus(seekdb_vr, milvus_vr)
            if not math.isnan(seekdb_vr) and not math.isnan(milvus_vr)
            else "N/A"
        )
        print(f"  {domain:<12}  {seekdb_vr:>10.1%}  {milvus_vr:>10.1%}  {diff_str}")
    print(f"{'='*60}\n")

    # ── Save results ──────────────────────────────────────────────────────────
    report = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "mode": "offline" if args.offline else "online",
        "target": "seekdb" if not args.offline else "offline",
        "config": {
            "host": args.host, "port": args.port,
            "domains": args.domains,
            "n_positives": args.n_positives,
            "n_negatives": args.n_negatives,
            "n_hard_negatives": args.n_hard_negatives,
        },
        "milvus_baseline": {d: MILVUS_BASELINE.get(d) for d in args.domains},
        "domain_results": {
            d: {k: v for k, v in dr.items() if k != "results"}
            for d, dr in domain_results.items()
        },
        "full_results": domain_results,
    }

    json_path = out_dir / f"{run_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    # Markdown summary
    md_lines = [
        f"# SeekDB MR-03 Semantic Campaign Report",
        f"",
        f"**Run ID**: {run_id}  ",
        f"**Mode**: {'Offline' if args.offline else f'SeekDB {args.host}:{args.port}'}  ",
        f"**Timestamp**: {report['timestamp']}  ",
        f"",
        "## Cross-Domain Differential (SeekDB vs Milvus)",
        "",
        "| Domain | SeekDB VR | Milvus VR | Diff |",
        "|--------|-----------|-----------|------|",
    ]
    for domain in args.domains:
        dr = domain_results.get(domain, {})
        sv = dr.get("violation_rate", float("nan"))
        mv = MILVUS_BASELINE.get(domain, float("nan"))
        diff_str = (
            _diff_vs_milvus(sv, mv)
            if not (math.isnan(sv) or math.isnan(mv)) else "N/A"
        )
        md_lines.append(f"| {domain} | {sv:.1%} | {mv:.1%} | {diff_str} |")

    md_lines += [
        "",
        "## Per-Domain Breakdown",
        "",
    ]
    for domain in args.domains:
        dr = domain_results.get(domain, {})
        md_lines.append(f"### {domain.upper()}")
        md_lines.append(f"- Total pairs: {dr.get('total', 0)}")
        md_lines.append(f"- Violations : {dr.get('violations', 0)}")
        md_lines.append(f"- Viol. rate : {dr.get('violation_rate', 0):.1%}")
        for pt, st in dr.get("by_type", {}).items():
            md_lines.append(
                f"  - {pt}: vr={st['violation_rate']:.1%} "
                f"avg_cos={st['avg_cosine']:.3f} ({st['violations']}/{st['total']})"
            )
        md_lines.append("")

    md_lines += [
        "## SeekDB Architectural Notes",
        "",
        "- SeekDB uses `l2_distance()` via MySQL-compatible SQL; cosine metric "
        "is not natively supported (L2 approximates ranking for normalised vectors).",
        "- `build_index` / `load` are no-ops — SeekDB manages indexing automatically.",
        "- Contracts that require HNSW `ef` parameter tuning (R5B IDX-003) are "
        "**N/A (architectural)** on SeekDB.",
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
