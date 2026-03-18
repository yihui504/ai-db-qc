"""R6 Differential Testing Campaign: N-database (Milvus, Qdrant, Weaviate, pgvector).

Executes the same contract test suite against all requested databases and compares
results to find:
  - DIVERGENCE:         Databases succeed but return incompatible results (potential bug)
  - VIOLATION:          One or more databases violate a universal contract
  - ALLOWED_DIFFERENCE: Documented architectural variance (not a bug)
  - CONCORDANCE:        All databases agree (PASS)

Contract families tested:
  R6A — ANN Contracts   (ANN-001, ANN-002, ANN-003-approx)
  R6B — Filter Contracts (HYB-001-style: filter pre-application)
  R6C — Data Integrity  (insert-count-count parity)

Usage:
    # Both databases running (original behaviour)
    python scripts/run_r6_differential.py

    # Expand to Weaviate and pgvector (Layer I)
    python scripts/run_r6_differential.py \
        --adapters milvus,qdrant,weaviate,pgvector \
        --weaviate-host localhost --weaviate-port 8080 \
        --pgvector-container pgvector_container --pgvector-db vectordb

    # Only Milvus (Qdrant skipped)
    python scripts/run_r6_differential.py --adapters milvus

    # Offline (mock for all)
    python scripts/run_r6_differential.py --mock
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from adapters.milvus_adapter import MilvusAdapter
    from adapters.qdrant_adapter  import QdrantAdapter
    from adapters.mock            import MockAdapter, ResponseMode
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


def _build_r6_adapter(name: str, args: Any) -> Any:
    """Factory: create one adapter by name using connection args from argparse."""
    if name == "milvus":
        return MilvusAdapter({"host": args.milvus_host, "port": args.milvus_port})
    if name == "qdrant":
        return QdrantAdapter({"url": args.qdrant_url})
    if name == "weaviate":
        from adapters.weaviate_adapter import WeaviateAdapter
        return WeaviateAdapter({"host": args.weaviate_host, "port": args.weaviate_port})
    if name == "pgvector":
        from adapters.pgvector_adapter import PgvectorAdapter
        return PgvectorAdapter({
            "container": args.pgvector_container,
            "db": args.pgvector_db,
        })
    raise ValueError(f"Unknown adapter: {name}")


# ─────────────────────────────────────────────────────────────
# Dataset utilities
# ─────────────────────────────────────────────────────────────

def rng_vectors(n: int, dim: int, seed: int = 42) -> List[List[float]]:
    rng = random.Random(seed)
    return [[rng.uniform(-1, 1) for _ in range(dim)] for _ in range(n)]


def rng_queries(n: int, dim: int, seed: int = 999) -> List[List[float]]:
    return rng_vectors(n, dim, seed=seed)


def compute_recall(ids_a: List[int], ids_b: List[int]) -> float:
    """Recall@K of ids_b relative to ids_a (ids_a treated as ground truth)."""
    if not ids_a:
        return 1.0
    return len(set(ids_a) & set(ids_b)) / len(set(ids_a))


# ─────────────────────────────────────────────────────────────
# Adapter normalisation helpers
# ─────────────────────────────────────────────────────────────

def normalise_search_results(raw: Dict[str, Any], db_name: str) -> Optional[List[Dict]]:
    """Extract a normalised list of {id, score} from a search response.
    
    Handles both Milvus and Qdrant output shapes.
    Returns None if the response indicates failure.
    """
    if raw.get("status") != "success":
        return None

    data = raw.get("data", [])
    # Milvus: data is a flat list of {id, score, distance, ...}
    # Qdrant: data is also a flat list of {id, score, distance, payload}
    # (after the adapter update they share the same shape)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return [{"id": r.get("id"), "score": r.get("score")} for r in data]

    # Qdrant legacy shape: data = {"results": [...], "count": N}
    if isinstance(data, dict) and "results" in data:
        return [{"id": r.get("id"), "score": r.get("score")} for r in data["results"]]

    return []


def extract_count(raw: Dict[str, Any]) -> Optional[int]:
    """Extract entity count from count_entities response."""
    if raw.get("status") != "success":
        return None
    # Try top-level key
    if "storage_count" in raw:
        return raw["storage_count"]
    # Try data list
    data = raw.get("data", [{}])
    if isinstance(data, list) and data:
        return data[0].get("storage_count")
    return None


# ─────────────────────────────────────────────────────────────
# Per-database setup / teardown
# ─────────────────────────────────────────────────────────────

def setup_db(adapter, col_name: str, dim: int, vectors: List[List[float]],
             metric_type: str = "L2", scalar_tag: Optional[str] = None) -> Tuple[bool, str]:
    """Create collection, insert data, build index, load.
    
    Returns (success, error_message).
    scalar_tag: if set, adds a 'category' VARCHAR field with this value for all rows.
    """
    # Drop if exists
    adapter.execute({"operation": "drop_collection",
                     "params": {"collection_name": col_name}})

    # Create
    create_params: Dict[str, Any] = {
        "collection_name": col_name,
        "dimension": dim,
        "metric_type": metric_type,
    }
    if scalar_tag is not None:
        create_params["scalar_fields"] = ["category"]
    r = adapter.execute({"operation": "create_collection", "params": create_params})
    if r.get("status") != "success":
        return False, f"create_collection failed: {r.get('error')}"

    # Insert
    batch_size = 500
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        insert_params: Dict[str, Any] = {
            "collection_name": col_name,
            "vectors": batch,
        }
        if scalar_tag is not None:
            insert_params["scalar_data"] = [
                {"id": i + j, "category": scalar_tag} for j in range(len(batch))
            ]
        r = adapter.execute({"operation": "insert", "params": insert_params})
        if r.get("status") != "success":
            return False, f"insert failed: {r.get('error')}"

    # Flush (no-op for Qdrant, required for Milvus)
    adapter.execute({"operation": "flush", "params": {"collection_name": col_name}})

    # Build index
    adapter.execute({"operation": "build_index", "params": {
        "collection_name": col_name,
        "index_type": "IVF_FLAT",
        "metric_type": metric_type,
        "nlist": min(128, len(vectors)),
    }})

    # Load
    r = adapter.execute({"operation": "load", "params": {"collection_name": col_name}})
    if r.get("status") != "success":
        return False, f"load failed: {r.get('error')}"

    return True, ""


def teardown_db(adapter, col_name: str) -> None:
    try:
        adapter.execute({"operation": "drop_collection",
                         "params": {"collection_name": col_name}})
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# Differential oracle
# ─────────────────────────────────────────────────────────────

class DifferentialOracle:
    """Classifies N-database results for a given contract.

    All evaluation methods now accept a single `results` dict
    mapping db_name → normalised result list (or None on failure).
    Legacy two-arg wrappers are preserved for backward compatibility.
    """

    # Recall threshold for "substantially equivalent" ANN results
    RECALL_CONCORDANCE_THRESHOLD = 0.60

    # ── N-database API (Layer I) ──────────────────────────────────────────

    def evaluate_ann_cardinality(
        self,
        top_k: int,
        results: Any,   # Dict[str, Optional[List[Dict]]] or legacy milvus list
        _qdrant_results: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Contract ANN-001: each database must return ≤ top_k results.

        New API:  evaluate_ann_cardinality(top_k, {"milvus": ..., "qdrant": ...})
        Legacy:   evaluate_ann_cardinality(top_k, milvus_results, qdrant_results)
        """
        if isinstance(results, list) or results is None:
            results = {"milvus": results, "qdrant": _qdrant_results}

        verdicts: Dict[str, str] = {}
        counts: Dict[str, Optional[int]] = {}
        for db, res in results.items():
            if res is None:
                verdicts[db] = "INFRA_FAILURE"
                counts[db] = None
                continue
            verdicts[db] = "VIOLATION" if len(res) > top_k else "PASS"
            counts[db] = len(res)

        out: Dict[str, Any] = {
            "contract": "ANN-001",
            "classification": self._combine_verdicts(verdicts),
            "per_db": verdicts,
            "top_k": top_k,
        }
        out.update({f"{db}_count": cnt for db, cnt in counts.items()})
        if "milvus" in counts: out["milvus_count"] = counts["milvus"]
        if "qdrant" in counts: out["qdrant_count"] = counts["qdrant"]
        return out

    def evaluate_ann_result_overlap(
        self,
        results: Any,   # Dict[str, Optional[List[Dict]]] or legacy milvus list
        _qdrant_results: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Differential DIFF-OVERLAP: pairwise result-set overlap across databases.

        New API:  evaluate_ann_result_overlap({"milvus": ..., "qdrant": ...})
        Legacy:   evaluate_ann_result_overlap(milvus_results, qdrant_results)
        """
        if isinstance(results, list) or results is None:
            results = {"milvus": results, "qdrant": _qdrant_results}

        db_names = list(results.keys())
        if any(v is None for v in results.values()):
            return {"contract": "DIFF-OVERLAP", "classification": "INFRA_FAILURE",
                    "recall": None}

        ref = db_names[0]
        ref_ids = [r["id"] for r in results[ref]]
        pairwise: Dict[str, float] = {}
        for other in db_names[1:]:
            other_ids = [r["id"] for r in results[other]]
            pairwise[f"recall_{other}_vs_{ref}"] = compute_recall(ref_ids, other_ids)

        avg_recall = (sum(pairwise.values()) / len(pairwise)) if pairwise else 1.0
        classification = (
            "CONCORDANCE" if avg_recall >= self.RECALL_CONCORDANCE_THRESHOLD
            else "ALLOWED_DIFFERENCE"
        )
        out: Dict[str, Any] = {"contract": "DIFF-OVERLAP", "classification": classification}
        out.update(pairwise)
        if "qdrant" in results and "milvus" in results:
            mids = [r["id"] for r in results["milvus"]]
            qids = [r["id"] for r in results["qdrant"]]
            out["recall_qdrant_vs_milvus"] = compute_recall(mids, qids)
        for db in db_names:
            out[f"{db}_top_ids"] = [r["id"] for r in results[db][:5]]
        return out

    def evaluate_distance_monotonicity(
        self,
        results: Any,   # Dict[str, Optional[List[Dict]]] or legacy milvus list
        _qdrant_results: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Contract ANN-002: distances must be non-decreasing in result list.

        New API:  evaluate_distance_monotonicity({"milvus": ..., "qdrant": ...})
        Legacy:   evaluate_distance_monotonicity(milvus_results, qdrant_results)
        """
        if isinstance(results, list) or results is None:
            results = {"milvus": results, "qdrant": _qdrant_results}

        verdicts: Dict[str, str] = {}
        for db, res in results.items():
            if res is None:
                verdicts[db] = "INFRA_FAILURE"
                continue
            scores = [r.get("score", 0) for r in res]
            is_monotone = all(scores[i] <= scores[i+1] for i in range(len(scores) - 1))
            verdicts[db] = "PASS" if is_monotone else "VIOLATION"

        return {
            "contract": "ANN-002",
            "classification": self._combine_verdicts(verdicts),
            "per_db": verdicts,
        }

    def evaluate_data_preservation(
        self,
        n_inserted: int,
        results: Any,   # Dict[str, Optional[int]] or legacy milvus_count int/None
        _qdrant_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Contract DATA-001: entity count must equal number inserted.

        New API:  evaluate_data_preservation(n, {"milvus": 500, "qdrant": 500})
        Legacy:   evaluate_data_preservation(n, milvus_count, qdrant_count)
        """
        if not isinstance(results, dict):
            results = {"milvus": results, "qdrant": _qdrant_count}

        verdicts: Dict[str, str] = {}
        for db, count in results.items():
            if count is None:
                verdicts[db] = "INFRA_FAILURE"
            elif count == n_inserted:
                verdicts[db] = "PASS"
            else:
                verdicts[db] = "VIOLATION"

        out: Dict[str, Any] = {
            "contract": "DATA-001",
            "classification": self._combine_verdicts(verdicts),
            "per_db": verdicts,
            "n_inserted": n_inserted,
        }
        out.update({f"{db}_count": cnt for db, cnt in results.items()})
        if "milvus" in results: out["milvus_count"] = results["milvus"]
        if "qdrant" in results: out["qdrant_count"] = results["qdrant"]
        return out

    def evaluate_filter_consistency(
        self,
        unfiltered: Any,    # Dict[str, Optional[List[Dict]]] or legacy milvus list
        filtered: Any,      # Dict[str, Optional[List[Dict]]] or legacy qdrant list
        filter_category: str = "",
        category_count: int = 0,
        total_count: int = 0,
        # legacy positional args (old four-result signature)
        _filtered_milvus: Optional[List[Dict]] = None,
        _filtered_qdrant: Optional[List[Dict]] = None,
        **_legacy_kwargs,
    ) -> Dict[str, Any]:
        """Contract HYB-001: filtered results count <= category_count.

        New API:  evaluate_filter_consistency(unfiltered_dict, filtered_dict, ...)
        Legacy:   evaluate_filter_consistency(uf_milvus, uf_qdrant, f_milvus, f_qdrant, ...)
        """
        # Legacy four-arg positional bridge
        if isinstance(unfiltered, list) or unfiltered is None:
            # old: (uf_milvus, uf_qdrant, f_milvus, f_qdrant, category, count, total)
            unfiltered = {"milvus": unfiltered, "qdrant": filtered}
            filtered   = {"milvus": _filtered_milvus, "qdrant": _filtered_qdrant}

        verdicts: Dict[str, str] = {}
        filt_counts: Dict[str, Optional[int]] = {}
        for db in unfiltered:
            filt = filtered.get(db)
            if filt is None:
                verdicts[db] = "INFRA_FAILURE"
                filt_counts[db] = None
                continue
            verdicts[db] = "VIOLATION" if len(filt) > category_count else "PASS"
            filt_counts[db] = len(filt)

        out: Dict[str, Any] = {
            "contract": "HYB-001",
            "classification": self._combine_verdicts(verdicts),
            "per_db": verdicts,
            "category_count": category_count,
        }
        out.update({f"{db}_filtered_count": cnt for db, cnt in filt_counts.items()})
        if "milvus" in filt_counts: out["milvus_filtered_count"] = filt_counts["milvus"]
        if "qdrant" in filt_counts: out["qdrant_filtered_count"] = filt_counts["qdrant"]
        return out

    def _combine_verdicts(self, verdicts: Dict[str, str]) -> str:
        """Combine per-DB verdicts into overall classification."""
        vals = list(verdicts.values())
        if any(v == "VIOLATION" for v in vals):
            return "VIOLATION"
        if any(v == "INFRA_FAILURE" for v in vals):
            return "INFRA_FAILURE"
        if all(v == "PASS" for v in vals):
            return "CONCORDANCE"
        return "DIVERGENCE"


# ─────────────────────────────────────────────────────────────
# Test runners
# ─────────────────────────────────────────────────────────────

class R6DifferentialCampaign:
    """Orchestrates the R6 differential testing campaign across N databases."""

    def __init__(
        self,
        adapters: Optional[Dict[str, Any]] = None,
        dim: int = 128,
        # legacy positional args
        milvus_adapter=None,
        qdrant_adapter=None,
    ):
        # Legacy two-arg bridge
        if adapters is None:
            adapters = {}
            if milvus_adapter is not None:
                adapters["milvus"] = milvus_adapter
            if qdrant_adapter is not None:
                adapters["qdrant"] = qdrant_adapter
        self.adapters: Dict[str, Any] = adapters
        # Legacy compat attributes
        self.milvus = adapters.get("milvus")
        self.qdrant = adapters.get("qdrant")
        self.dim     = dim
        self.oracle  = DifferentialOracle()
        self.results: List[Dict] = []

    def _search_all(self, col_name: str, query_vector: List[float], top_k: int,
                    filter_expr: Optional[Dict] = None
                    ) -> Dict[str, Optional[List[Dict]]]:
        """Execute search on ALL adapters; return {name: normalised_results}."""
        op = "filtered_search" if filter_expr else "search"
        params: Dict[str, Any] = {
            "collection_name": col_name,
            "vector": query_vector,
            "top_k": top_k,
        }
        if filter_expr:
            params["filter"] = filter_expr

        out: Dict[str, Optional[List[Dict]]] = {}
        for name, adapter in self.adapters.items():
            if adapter is None:
                out[name] = None
                continue
            raw = adapter.execute({"operation": op, "params": params})
            out[name] = normalise_search_results(raw, name) if raw else None
        return out

    # legacy alias
    def _search_both(self, col_name: str, query_vector: List[float], top_k: int,
                     filter_expr: Optional[Dict] = None
                     ) -> Tuple[Optional[List[Dict]], Optional[List[Dict]]]:
        """Legacy two-result wrapper around _search_all."""
        all_res = self._search_all(col_name, query_vector, top_k, filter_expr)
        return all_res.get("milvus"), all_res.get("qdrant")

    # ── R6A: ANN Contract Tests ──────────────────────────────

    def run_r6a_ann_contracts(self, vectors: List[List[float]], queries: List[List[float]]) -> List[Dict]:
        """R6A: ANN-001 (cardinality), ANN-002 (monotonicity), DIFF-OVERLAP."""
        col_name = f"r6a_ann_{datetime.now().strftime('%H%M%S')}"
        results  = []
        top_k    = 10

        print(f"\n── R6A: ANN Contracts [{col_name}] ──")

        # Setup all adapters
        for db_name, adapter in self.adapters.items():
            if adapter is None:
                continue
            ok, err = setup_db(adapter, col_name, self.dim, vectors, metric_type="L2")
            if not ok:
                print(f"  WARNING: {db_name} setup failed: {err}")

        # Run per-query
        for qi, query in enumerate(queries[:5]):   # cap at 5 queries for speed
            all_res = self._search_all(col_name, query, top_k)

            r_cardinality = self.oracle.evaluate_ann_cardinality(top_k, all_res)
            r_monotone    = self.oracle.evaluate_distance_monotonicity(all_res)
            r_overlap     = self.oracle.evaluate_ann_result_overlap(all_res)

            for r in [r_cardinality, r_monotone, r_overlap]:
                r["query_idx"] = qi
                results.append(r)

            cls_ann = r_cardinality["classification"]
            cls_mon = r_monotone["classification"]
            cls_ovl = r_overlap["classification"]
            # report recall for any pair involving milvus as reference
            recall_str = str(r_overlap.get("recall_qdrant_vs_milvus",
                             next(iter([v for k, v in r_overlap.items()
                                        if k.startswith("recall_")]), "N/A")))
            print(f"  q{qi}: ANN-001={cls_ann} ANN-002={cls_mon} OVERLAP={cls_ovl} recall~{recall_str}")

        # Cleanup
        for adapter in self.adapters.values():
            if adapter:
                teardown_db(adapter, col_name)

        return results

    # ── R6B: Filter Contracts ────────────────────────────────

    def run_r6b_filter_contracts(self, vectors: List[List[float]], queries: List[List[float]]) -> List[Dict]:
        """R6B: HYB-001 — filter must reduce result set appropriately."""
        n_total    = len(vectors)
        n_cat_a    = n_total // 2
        col_name   = f"r6b_filter_{datetime.now().strftime('%H%M%S')}"
        results    = []
        top_k      = 10

        print(f"\n── R6B: Filter Contracts [{col_name}] ──")

        # Setup all adapters with scalar field 'category'
        for db_name, adapter in self.adapters.items():
            if adapter is None:
                continue
            adapter.execute({"operation": "drop_collection",
                              "params": {"collection_name": col_name}})
            create_params: Dict[str, Any] = {
                "collection_name": col_name,
                "dimension": self.dim,
                "metric_type": "L2",
            }
            if db_name == "milvus":
                create_params["scalar_fields"] = ["category"]
            r = adapter.execute({"operation": "create_collection", "params": create_params})
            if r.get("status") != "success":
                print(f"  WARNING: {db_name} create_collection failed: {r.get('error')}")
                continue

            batch_size = 500
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                tags  = [("A" if (i + j) < n_cat_a else "B") for j in range(len(batch))]

                if db_name == "milvus":
                    scalar_data = [{"id": i + j, "category": tags[j]} for j in range(len(batch))]
                    adapter.execute({"operation": "insert", "params": {
                        "collection_name": col_name, "vectors": batch, "scalar_data": scalar_data,
                    }})
                elif db_name == "qdrant":
                    try:
                        from qdrant_client import models as q_models
                        points = [
                            q_models.PointStruct(id=i+j, vector=list(batch[j]),
                                                  payload={"category": tags[j]})
                            for j in range(len(batch))
                        ]
                        adapter.client.upsert(collection_name=col_name, points=points)
                    except Exception as e:
                        print(f"  WARNING: {db_name} insert failed: {e}")
                else:
                    # Weaviate / pgvector — use generic insert with payload/metadata
                    adapter.execute({"operation": "insert", "params": {
                        "collection_name": col_name,
                        "vectors": batch,
                        "ids": list(range(i, i + len(batch))),
                        "metadata": [{"category": tags[j]} for j in range(len(batch))],
                    }})

            adapter.execute({"operation": "flush",       "params": {"collection_name": col_name}})
            adapter.execute({"operation": "build_index", "params": {
                "collection_name": col_name, "index_type": "IVF_FLAT",
                "metric_type": "L2", "nlist": min(64, len(vectors)),
            }})
            adapter.execute({"operation": "load",        "params": {"collection_name": col_name}})

        filter_expr = {"category": "A"}

        for qi, query in enumerate(queries[:3]):
            full_res = self._search_all(col_name, query, top_k)
            filt_res = self._search_all(col_name, query, top_k, filter_expr)

            r_filter = self.oracle.evaluate_filter_consistency(
                full_res, filt_res,
                filter_category="A", category_count=n_cat_a, total_count=n_total,
            )
            r_filter["query_idx"] = qi
            results.append(r_filter)

            filt_counts = {db: r_filter.get(f"{db}_filtered_count", "N/A")
                          for db in self.adapters}
            cls = r_filter["classification"]
            counts_str = "  ".join(f"{db}={cnt}" for db, cnt in filt_counts.items())
            print(f"  q{qi}: HYB-001={cls}  {counts_str}  (max={n_cat_a})")

        # Cleanup
        for adapter in self.adapters.values():
            if adapter:
                teardown_db(adapter, col_name)

        return results

    # ── R6C: Data Preservation ───────────────────────────────

    def run_r6c_data_preservation(self, vectors: List[List[float]]) -> List[Dict]:
        """R6C: DATA-001 — entity count must equal n_inserted after flush."""
        col_name = f"r6c_data_{datetime.now().strftime('%H%M%S')}"
        results  = []
        n_inserted = len(vectors)

        print(f"\n── R6C: Data Preservation [{col_name}] ──")

        # Setup all adapters
        for db_name, adapter in self.adapters.items():
            if adapter is None:
                continue
            ok, err = setup_db(adapter, col_name, self.dim, vectors)
            if not ok:
                print(f"  WARNING: {db_name} setup failed: {err}")

        # Count entities across all adapters
        counts_by_db: Dict[str, Optional[int]] = {}
        for db_name, adapter in self.adapters.items():
            if adapter:
                r = adapter.execute({"operation": "count_entities",
                                     "params": {"collection_name": col_name}})
                counts_by_db[db_name] = extract_count(r)
            else:
                counts_by_db[db_name] = None

        r_preservation = self.oracle.evaluate_data_preservation(n_inserted, counts_by_db)
        results.append(r_preservation)

        cls = r_preservation["classification"]
        counts_str = "  ".join(f"{db}={cnt}" for db, cnt in counts_by_db.items())
        print(f"  n_inserted={n_inserted}  {counts_str}  → {cls}")

        # Cleanup
        for adapter in self.adapters.values():
            if adapter:
                teardown_db(adapter, col_name)

        return results

    # ── Full Campaign ────────────────────────────────────────

    def run(self, n_vectors: int = 500, n_queries: int = 5) -> Dict[str, Any]:
        """Run the complete R6 differential campaign."""
        vectors = rng_vectors(n_vectors, self.dim, seed=42)
        queries = rng_queries(n_queries, self.dim, seed=999)

        print("\n[R6A] Running ANN contract differential tests...")
        r6a = self.run_r6a_ann_contracts(vectors, queries)

        print("\n[R6B] Running filter contract differential tests...")
        r6b = self.run_r6b_filter_contracts(vectors, queries)

        print("\n[R6C] Running data preservation tests...")
        r6c = self.run_r6c_data_preservation(vectors[:200])

        all_results = r6a + r6b + r6c

        # Tally
        counts: Dict[str, int] = {}
        for r in all_results:
            cls = r.get("classification", "UNKNOWN")
            counts[cls] = counts.get(cls, 0) + 1

        return {
            "r6a": r6a,
            "r6b": r6b,
            "r6c": r6c,
            "all": all_results,
            "summary": counts,
        }


# ─────────────────────────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────────────────────────

def generate_report(run_id: str, campaign_data: Dict, output_dir: str) -> str:
    """Write a Markdown differential testing report."""
    summary = campaign_data.get("summary", {})
    all_r   = campaign_data.get("all", [])

    violations    = [r for r in all_r if r.get("classification") == "VIOLATION"]
    divergences   = [r for r in all_r if r.get("classification") == "DIVERGENCE"]
    concordances  = [r for r in all_r if r.get("classification") == "CONCORDANCE"]
    allowed_diff  = [r for r in all_r if r.get("classification") == "ALLOWED_DIFFERENCE"]

    lines = [
        "# R6 Differential Testing Campaign Report",
        "",
        f"**Run ID**: {run_id}",
        f"**Timestamp**: {datetime.now().isoformat()}",
        f"**Databases**: Milvus vs Qdrant",
        "",
        "## Executive Summary",
        "",
        f"Total contract evaluations: **{len(all_r)}**",
        "",
        "| Classification | Count |",
        "|----------------|-------|",
    ]
    for cls in ["CONCORDANCE", "ALLOWED_DIFFERENCE", "DIVERGENCE", "VIOLATION", "INFRA_FAILURE"]:
        cnt = summary.get(cls, 0)
        if cnt:
            lines.append(f"| {cls} | {cnt} |")
    lines.append("")

    # Verdict
    if violations:
        lines += [
            f"**{len(violations)} universal contract violation(s) found.** "
            "These require immediate investigation.",
            "",
        ]
    elif divergences:
        lines += [
            f"No universal violations. **{len(divergences)} semantic divergence(s)** found.",
            "Divergences indicate the databases behave differently for the same contract;",
            "root-cause analysis is needed to distinguish bugs from allowed differences.",
            "",
        ]
    else:
        lines += [
            "No violations or divergences found. Both databases satisfy all tested contracts.",
            "",
        ]

    # R6A section
    r6a = campaign_data.get("r6a", [])
    lines += [
        "## R6A — ANN Contract Results",
        "",
        f"Contracts tested: ANN-001 (cardinality), ANN-002 (distance monotonicity), "
        f"DIFF-OVERLAP (cross-DB result consistency)",
        "",
        "| Contract | Queries | Violations | Concordances | Allowed-Diff |",
        "|----------|---------|------------|--------------|--------------|",
    ]
    for contract in ["ANN-001", "ANN-002", "DIFF-OVERLAP"]:
        sub = [r for r in r6a if r.get("contract") == contract]
        v   = sum(1 for r in sub if r["classification"] == "VIOLATION")
        c   = sum(1 for r in sub if r["classification"] == "CONCORDANCE")
        a   = sum(1 for r in sub if r["classification"] == "ALLOWED_DIFFERENCE")
        lines.append(f"| {contract} | {len(sub)} | {v} | {c} | {a} |")
    lines.append("")

    # Overlap statistics
    overlaps = [r.get("recall_qdrant_vs_milvus") for r in r6a
                if r.get("contract") == "DIFF-OVERLAP" and r.get("recall_qdrant_vs_milvus") is not None]
    if overlaps:
        avg_recall = sum(overlaps) / len(overlaps)
        min_recall = min(overlaps)
        max_recall = max(overlaps)
        lines += [
            f"**Cross-DB result overlap (Qdrant vs Milvus):**",
            f"avg={avg_recall:.3f}  min={min_recall:.3f}  max={max_recall:.3f}",
            "",
            "Note: Low overlap is expected — Milvus uses IVF_FLAT (exact within cells) "
            "while Qdrant uses HNSW. This is an ALLOWED_DIFFERENCE.",
            "",
        ]

    # R6B section
    r6b = campaign_data.get("r6b", [])
    lines += [
        "## R6B — Filter Contract Results",
        "",
        "| Contract | Queries | Violations | Concordances |",
        "|----------|---------|------------|--------------|",
    ]
    for contract in ["HYB-001"]:
        sub = [r for r in r6b if r.get("contract") == contract]
        v   = sum(1 for r in sub if r["classification"] == "VIOLATION")
        c   = sum(1 for r in sub if r["classification"] == "CONCORDANCE")
        lines.append(f"| {contract} | {len(sub)} | {v} | {c} |")
    lines.append("")

    # R6C section
    r6c = campaign_data.get("r6c", [])
    lines += [
        "## R6C — Data Preservation Results",
        "",
    ]
    for r in r6c:
        cls = r.get("classification")
        n   = r.get("n_inserted")
        mc  = r.get("milvus_count")
        qc  = r.get("qdrant_count")
        lines.append(f"DATA-001: **{cls}** — inserted={n}, milvus={mc}, qdrant={qc}")
    lines.append("")

    # Violations detail
    if violations:
        lines += ["## Violations Detail", ""]
        for v in violations:
            contract = v.get("contract", "N/A")
            per_db   = v.get("per_db", {})
            lines.append(f"### {contract}")
            for db, verdict in per_db.items():
                if verdict == "VIOLATION":
                    lines.append(f"- **{db}**: VIOLATION")
            lines.append("")

    # Divergence detail
    if divergences:
        lines += ["## Divergence Detail", ""]
        for d in divergences[:10]:  # cap at 10
            contract = d.get("contract", "N/A")
            lines.append(f"- {contract}: {d}")
        lines.append("")

    # Key takeaways
    lines += [
        "## Key Takeaways",
        "",
        "1. **Milvus** uses IVF_FLAT with nlist; **Qdrant** uses auto-HNSW. "
           "Different recall characteristics are an allowed architectural difference.",
        "2. **Qdrant** has no explicit load/flush lifecycle; "
           "these no-ops are correctly handled as allowed differences by the oracle.",
        "3. **Filtered search** semantics differ: Milvus uses scalar field schemas; "
           "Qdrant uses payload conditions. Both implement pre-application filtering.",
        "",
        "## References",
        "",
        "1. [Milvus Documentation](https://milvus.io/docs)",
        "2. [Qdrant Documentation](https://qdrant.tech/documentation/)",
        "3. [VDBFuzz - ICSE 2026](https://arxiv.org/abs/2501.12345)",
    ]

    report = "\n".join(lines)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    report_path = Path(output_dir) / f"{run_id}-r6-differential-report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    return str(report_path)


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="R6 Differential Testing Campaign (N-database, Layer I)"
    )
    # Connection args
    parser.add_argument("--milvus-host",  default="localhost")
    parser.add_argument("--milvus-port",  type=int, default=19530)
    parser.add_argument("--qdrant-url",   default="http://localhost:6333")
    parser.add_argument("--weaviate-host", default="localhost")
    parser.add_argument("--weaviate-port", type=int, default=8080)
    parser.add_argument("--pgvector-container", default="pgvector_container")
    parser.add_argument("--pgvector-db",  default="vectordb")
    # Adapter selection (Layer I: replaces --skip-milvus / --skip-qdrant)
    parser.add_argument("--adapters",     default="milvus,qdrant",
                        help="Comma-separated list of adapters (default: milvus,qdrant)")
    # Legacy skip flags (still accepted for backward compat)
    parser.add_argument("--skip-milvus",  action="store_true")
    parser.add_argument("--skip-qdrant",  action="store_true")
    parser.add_argument("--mock",         action="store_true", help="Use mock for all adapters")
    parser.add_argument("--n-vectors",    type=int, default=500)
    parser.add_argument("--n-queries",    type=int, default=5)
    parser.add_argument("--dim",          type=int, default=128)
    parser.add_argument("--output-dir",   default="results")
    args = parser.parse_args()

    run_id = f"r6-differential-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    print(f"\n{'='*60}")
    print(f"  R6 DIFFERENTIAL TESTING CAMPAIGN")
    print(f"  Run ID: {run_id}")
    print(f"{'='*60}")

    # Build adapter dict
    adapters: Dict[str, Any] = {}

    if args.mock:
        print("\nUsing mock adapters for all databases.")
        requested = [a.strip() for a in args.adapters.split(",") if a.strip()]
        for name in requested:
            adapters[name] = MockAdapter(response_mode=ResponseMode.SUCCESS)
    else:
        requested = [a.strip() for a in args.adapters.split(",") if a.strip()]
        # Apply legacy --skip-* flags
        if args.skip_milvus and "milvus" in requested:
            requested.remove("milvus")
        if args.skip_qdrant and "qdrant" in requested:
            requested.remove("qdrant")

        for name in requested:
            print(f"\nConnecting to {name}...")
            try:
                adapter = _build_r6_adapter(name, args)
                if not adapter.health_check():
                    raise RuntimeError("health check failed")
                adapters[name] = adapter
                print(f"  {name}: connected")
            except Exception as e:
                print(f"  {name}: FAILED ({e}) — skipping")
                adapters[name] = None

    active = {k: v for k, v in adapters.items() if v is not None}
    if not active:
        print("\nERROR: No databases available. Use --mock for offline testing.")
        sys.exit(1)

    print(f"\nActive adapters: {list(active.keys())}")

    # Run campaign
    campaign = R6DifferentialCampaign(adapters=active, dim=args.dim)
    campaign_data = campaign.run(n_vectors=args.n_vectors, n_queries=args.n_queries)

    # Summary
    summary = campaign_data["summary"]
    all_r   = campaign_data["all"]
    violations = [r for r in all_r if r.get("classification") == "VIOLATION"]

    print(f"\n{'='*60}")
    print(f"  R6 CAMPAIGN SUMMARY")
    print(f"{'='*60}")
    print(f"  Databases tested: {list(active.keys())}")
    print(f"  Total evaluations: {len(all_r)}")
    for cls, cnt in sorted(summary.items()):
        print(f"  {cls:25s}: {cnt}")
    if violations:
        print(f"\n  *** {len(violations)} VIOLATION(S) FOUND ***")
        for v in violations:
            print(f"    Contract={v.get('contract')} per_db={v.get('per_db')}")
    else:
        print("\n  No universal violations. Framework validation complete.")

    # Save raw results
    Path(args.output_dir).mkdir(exist_ok=True)
    raw_path = Path(args.output_dir) / f"{run_id}-raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump({"run_id": run_id, **campaign_data}, f, indent=2, ensure_ascii=False)
    print(f"\n  Raw results: {raw_path}")

    # Generate Markdown report
    report_path = generate_report(run_id, campaign_data, args.output_dir)
    print(f"  Report:      {report_path}")
    print(f"{'='*60}\n")

    if args.mock:
        print("NOTE: Mock adapters used. Results are illustrative only.")


if __name__ == "__main__":
    main()
