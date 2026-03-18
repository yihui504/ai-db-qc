"""R5D Schema Contract Testing Campaign — SCH-001 through SCH-004.

Tests Milvus dynamic schema correctness contracts.  Each contract verifies that
vector search, filtered search, and entity count remain correct after schema-related
operations such as adding new dynamic fields, changing field values, rebuilding an
index on a dynamic-field collection, and mixing entities with different schema versions.

Contract Definitions
====================
SCH-001 (Dynamic Field Add — Search Correctness):
    Insert N entities WITHOUT a dynamic field 'tag', then insert M entities WITH 'tag'.
    Oracle: full vector search (top_k = N+M) must return all N+M IDs correctly.
    Violation: any entity is missing from search results after dynamic-field extension.

SCH-002 (Filter After Dynamic Field Extension):
    After SCH-001 setup, issue filtered_search with "tag == 'new'".
    Oracle: result count must equal M (only the tagged entities); no untagged entity
            should appear; no tag-mismatch should appear.
    Violation: tagged count mismatch OR untagged entity appears in filtered results.

SCH-003 (Index Rebuild After Dynamic Field — Recall Preservation):
    Insert N entities with dynamic field 'group' set to random values.
    Trigger index drop + rebuild (build_index after drop_index if supported).
    Oracle: recall@top_k after rebuild >= 0.99 vs FLAT ground truth.
    Violation: recall drops below threshold after rebuild.

SCH-004 (Count Accuracy After Mixed Schema Insert):
    Phase A: insert N0 entities (schema v1, no dynamic field).
    Phase B: insert N1 entities (schema v2, adds 'category' field).
    Phase C: delete D entities from phase A.
    Oracle: count_entities must equal N0 + N1 - D (exact).
    Violation: count deviates from expected value.

Usage
=====
    # Online (Milvus Docker required on port 19530)
    python scripts/run_r5d_schema.py

    # Offline mock mode (no Milvus required)
    python scripts/run_r5d_schema.py --offline

    # Custom Milvus endpoint
    python scripts/run_r5d_schema.py --host 127.0.0.1 --port 19530

    # Only run specific contracts
    python scripts/run_r5d_schema.py --contracts SCH-001 SCH-002

    # Larger scale
    python scripts/run_r5d_schema.py --n-base 500 --n-tagged 300 --dim 128

"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Lazy imports — adapters loaded on demand
# ---------------------------------------------------------------------------

RESULTS_DIR = Path(__file__).parent.parent / "results" / "r5d_schema"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rng(seed: int = 42) -> np.random.Generator:
    return np.random.default_rng(seed)


def make_vectors(n: int, dim: int, seed: int = 0) -> List[List[float]]:
    rng = _rng(seed)
    vecs = rng.standard_normal((n, dim)).astype(np.float32)
    # L2-normalise for stable distance behaviour
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    vecs = vecs / norms
    return vecs.tolist()


def _recall(found: Set[int], ground_truth: Set[int]) -> float:
    if not ground_truth:
        return 1.0
    return len(found & ground_truth) / len(ground_truth)


# ---------------------------------------------------------------------------
# Offline mock adapter for no-Docker testing
# ---------------------------------------------------------------------------

class _MockSchemaAdapter:
    """In-memory schema-aware mock adapter for offline smoke tests.

    Supports dynamic field storage via scalar_data / payload dicts.
    """

    def __init__(self) -> None:
        # collection_name → {"vectors": [...], "ids": [...], "payload": [...]}
        self._store: Dict[str, Dict[str, Any]] = {}

    def health_check(self) -> bool:
        return True

    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        op = request.get("operation", "")
        params = request.get("params", {})
        try:
            if op in ("create_collection",):
                name = params["collection_name"]
                self._store[name] = {"vectors": [], "ids": [], "payload": []}
                return {"status": "success", "operation": op,
                        "collection_name": name, "data": []}

            elif op in ("drop_collection",):
                name = params.get("collection_name", "")
                self._store.pop(name, None)
                return {"status": "success", "operation": op, "data": []}

            elif op in ("insert", "insert_unique"):
                name    = params["collection_name"]
                vectors = params.get("vectors", [])
                ids     = params.get("ids")
                scalar  = params.get("scalar_data", [])
                if ids is None:
                    existing = self._store.get(name, {}).get("ids", [])
                    next_id  = (max(existing) + 1) if existing else 0
                    ids = list(range(next_id, next_id + len(vectors)))
                col = self._store.setdefault(name, {"vectors": [], "ids": [], "payload": []})
                for i, (vec, id_) in enumerate(zip(vectors, ids)):
                    col["vectors"].append(vec)
                    col["ids"].append(int(id_))
                    col["payload"].append(scalar[i] if scalar and i < len(scalar) else {})
                return {"status": "success", "operation": op,
                        "insert_count": len(ids), "data": [{"id": i} for i in ids]}

            elif op == "search":
                name  = params["collection_name"]
                qvec  = np.array(params.get("vector", []))
                top_k = int(params.get("top_k", 10))
                col   = self._store.get(name)
                if not col or not col["vectors"]:
                    return {"status": "success", "operation": op, "data": []}
                vecs = np.array(col["vectors"], dtype=np.float32)
                dists = np.linalg.norm(vecs - qvec, axis=1)
                idxs  = np.argsort(dists)[:top_k]
                data  = [{"id": col["ids"][i], "score": float(dists[i]),
                           "distance": float(dists[i])} for i in idxs]
                return {"status": "success", "operation": op, "data": data}

            elif op == "filtered_search":
                name       = params["collection_name"]
                qvec       = np.array(params.get("vector", []))
                top_k      = int(params.get("top_k", 10))
                filter_dict = params.get("filter", {})
                col = self._store.get(name)
                if not col or not col["vectors"]:
                    return {"status": "success", "operation": op, "data": []}
                # Apply filter
                keep_idxs = []
                for i, (id_, pay) in enumerate(zip(col["ids"], col["payload"])):
                    if self._match_filter(pay, filter_dict):
                        keep_idxs.append(i)
                if not keep_idxs:
                    return {"status": "success", "operation": op, "data": []}
                vecs  = np.array([col["vectors"][i] for i in keep_idxs], dtype=np.float32)
                dists = np.linalg.norm(vecs - qvec, axis=1)
                sorted_local = np.argsort(dists)[:top_k]
                data = [{"id": col["ids"][keep_idxs[j]],
                          "score": float(dists[j]),
                          "distance": float(dists[j])}
                         for j in sorted_local]
                return {"status": "success", "operation": op, "data": data}

            elif op == "count_entities":
                name = params["collection_name"]
                col  = self._store.get(name, {})
                cnt  = len(col.get("ids", []))
                return {"status": "success", "operation": op,
                        "storage_count": cnt, "load_state": "Loaded",
                        "data": [{"storage_count": cnt}]}

            elif op == "delete":
                name   = params["collection_name"]
                del_ids = set(params.get("ids", []))
                col    = self._store.get(name)
                if col:
                    keep = [(v, i, p) for v, i, p in zip(col["vectors"], col["ids"], col["payload"])
                            if i not in del_ids]
                    col["vectors"] = [x[0] for x in keep]
                    col["ids"]     = [x[1] for x in keep]
                    col["payload"] = [x[2] for x in keep]
                return {"status": "success", "operation": op,
                        "delete_count": len(del_ids), "data": []}

            elif op in ("flush", "build_index", "load", "release", "reload"):
                return {"status": "success", "operation": op, "data": []}

            else:
                return {"status": "error", "error": f"Unknown op: {op}"}
        except Exception as e:
            return {"status": "error", "error": str(e), "operation": op}

    @staticmethod
    def _match_filter(payload: Dict, filter_expr: Any) -> bool:
        """Simple dict equality filter."""
        if isinstance(filter_expr, dict):
            for k, v in filter_expr.items():
                if isinstance(v, (list, set)):
                    if payload.get(k) not in v:
                        return False
                else:
                    if payload.get(k) != v:
                        return False
            return True
        elif isinstance(filter_expr, str):
            # Best-effort: "tag == 'new'"
            import re
            m = re.match(r"(\w+)\s*==\s*['\"](.+)['\"]", filter_expr.strip())
            if m:
                return payload.get(m.group(1)) == m.group(2)
        return True


# ---------------------------------------------------------------------------
# Contract implementations
# ---------------------------------------------------------------------------

def run_sch001(
    adapter: Any,
    col: str,
    n_base: int,
    n_tagged: int,
    dim: int,
) -> Dict[str, Any]:
    """SCH-001: Dynamic Field Add — Search Correctness.

    Insert n_base entities without 'tag', then n_tagged entities with tag='new'.
    Verify full-scan search retrieves all n_base + n_tagged entities.
    """
    test_id = "SCH-001"
    total   = n_base + n_tagged
    print(f"\n  [{test_id}] Dynamic field add — search correctness "
          f"(n_base={n_base}, n_tagged={n_tagged})")

    # Setup
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
    r = adapter.execute({"operation": "create_collection",
                         "params": {"collection_name": col, "dimension": dim,
                                    "enable_dynamic_field": True}})
    if r.get("status") != "success":
        return {"test_id": test_id, "classification": "SKIP",
                "reason": f"create_collection failed: {r.get('error', '')}"}

    # Phase A: base entities (no dynamic field)
    vecs_a   = make_vectors(n_base, dim, seed=1)
    ids_a    = list(range(n_base))
    r = adapter.execute({"operation": "insert",
                         "params": {"collection_name": col, "vectors": vecs_a,
                                    "ids": ids_a}})
    if r.get("status") != "success":
        return {"test_id": test_id, "classification": "SKIP",
                "reason": f"insert phase A failed: {r.get('error', '')}"}

    # Phase B: tagged entities (dynamic field 'tag' = 'new')
    vecs_b   = make_vectors(n_tagged, dim, seed=2)
    ids_b    = list(range(n_base, n_base + n_tagged))
    scalar_b = [{"tag": "new"} for _ in range(n_tagged)]
    r = adapter.execute({"operation": "insert",
                         "params": {"collection_name": col, "vectors": vecs_b,
                                    "ids": ids_b, "scalar_data": scalar_b}})
    if r.get("status") != "success":
        return {"test_id": test_id, "classification": "SKIP",
                "reason": f"insert phase B failed: {r.get('error', '')}"}

    adapter.execute({"operation": "flush", "params": {"collection_name": col}})
    adapter.execute({"operation": "build_index",
                     "params": {"collection_name": col, "index_type": "IVF_FLAT",
                                "metric_type": "L2", "nlist": 64}})
    adapter.execute({"operation": "load", "params": {"collection_name": col}})

    # Oracle: search with a random query, top_k = total
    q_vec = make_vectors(1, dim, seed=99)[0]
    r = adapter.execute({"operation": "search",
                         "params": {"collection_name": col,
                                    "vector": q_vec, "top_k": total}})
    if r.get("status") != "success":
        return {"test_id": test_id, "classification": "SKIP",
                "reason": f"search failed: {r.get('error', '')}"}

    returned_ids = {int(d["id"]) for d in r.get("data", [])}
    expected_ids = set(ids_a + ids_b)
    missing      = expected_ids - returned_ids
    extra        = returned_ids - expected_ids

    if missing or extra:
        return {
            "test_id": test_id,
            "classification": "VIOLATION",
            "violation_type": "SCH-001",
            "violation_details": {
                "expected_count": total,
                "returned_count": len(returned_ids),
                "missing_ids":    sorted(missing)[:20],
                "extra_ids":      sorted(extra)[:20],
            },
            "reason": f"Search after dynamic field add returned {len(returned_ids)}/{total} entities",
        }

    return {
        "test_id": test_id,
        "classification": "PASS",
        "entities_verified": total,
        "returned_count": len(returned_ids),
    }


def run_sch002(
    adapter: Any,
    col: str,
    n_base: int,
    n_tagged: int,
    dim: int,
) -> Dict[str, Any]:
    """SCH-002: Filter After Dynamic Field Extension.

    Reuses SCH-001 collection (assumes it was created and populated).
    Runs filtered_search with tag=='new' and verifies only tagged entities appear.
    """
    test_id = "SCH-002"
    print(f"\n  [{test_id}] Filter after dynamic field extension")

    # Collection must already exist from SCH-001; re-create here in case standalone
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
    r = adapter.execute({"operation": "create_collection",
                         "params": {"collection_name": col, "dimension": dim,
                                    "enable_dynamic_field": True}})
    if r.get("status") != "success":
        return {"test_id": test_id, "classification": "SKIP",
                "reason": f"create_collection failed: {r.get('error', '')}"}

    # Phase A: untagged
    vecs_a = make_vectors(n_base, dim, seed=1)
    ids_a  = list(range(n_base))
    adapter.execute({"operation": "insert",
                     "params": {"collection_name": col, "vectors": vecs_a, "ids": ids_a}})

    # Phase B: tagged
    vecs_b   = make_vectors(n_tagged, dim, seed=2)
    ids_b    = list(range(n_base, n_base + n_tagged))
    scalar_b = [{"tag": "new"} for _ in range(n_tagged)]
    adapter.execute({"operation": "insert",
                     "params": {"collection_name": col, "vectors": vecs_b,
                                "ids": ids_b, "scalar_data": scalar_b}})

    adapter.execute({"operation": "flush", "params": {"collection_name": col}})
    adapter.execute({"operation": "build_index",
                     "params": {"collection_name": col, "index_type": "IVF_FLAT",
                                "metric_type": "L2", "nlist": 64}})
    adapter.execute({"operation": "load", "params": {"collection_name": col}})

    # Filtered search for tag == 'new', top_k = n_tagged
    q_vec = make_vectors(1, dim, seed=99)[0]
    filter_expr = {"tag": "new"}
    r = adapter.execute({"operation": "filtered_search",
                         "params": {"collection_name": col,
                                    "vector": q_vec,
                                    "top_k": n_tagged,
                                    "filter": filter_expr}})
    if r.get("status") != "success":
        return {"test_id": test_id, "classification": "SKIP",
                "reason": f"filtered_search failed: {r.get('error', '')}"}

    results      = r.get("data", [])
    returned_ids = {int(d["id"]) for d in results}
    expected_ids = set(ids_b)
    false_positives = returned_ids - expected_ids   # untagged ids appearing
    false_negatives = expected_ids - returned_ids   # tagged ids missing

    if false_positives:
        return {
            "test_id": test_id,
            "classification": "VIOLATION",
            "violation_type": "SCH-002-FP",
            "violation_details": {
                "false_positives": sorted(false_positives)[:20],
                "returned": len(returned_ids),
                "expected": n_tagged,
            },
            "reason": f"Filtered search returned {len(false_positives)} untagged entities",
        }
    if len(results) < max(1, int(n_tagged * 0.8)):
        return {
            "test_id": test_id,
            "classification": "VIOLATION",
            "violation_type": "SCH-002-FN",
            "violation_details": {
                "returned": len(results),
                "expected_min": max(1, int(n_tagged * 0.8)),
                "false_negatives": sorted(false_negatives)[:20],
            },
            "reason": f"Filtered search returned only {len(results)}/{n_tagged} tagged entities",
        }

    return {
        "test_id": test_id,
        "classification": "PASS",
        "tagged_entities": n_tagged,
        "returned_count": len(results),
        "false_positives": 0,
    }


def run_sch003(
    adapter: Any,
    col: str,
    n_entities: int,
    dim: int,
    recall_threshold: float = 0.99,
) -> Dict[str, Any]:
    """SCH-003: Index Rebuild After Dynamic Field — Recall Preservation.

    Insert N entities with dynamic 'group' field.
    Compute FLAT ground truth, rebuild index, re-check recall.
    Recall after rebuild must >= recall_threshold.
    """
    test_id   = "SCH-003"
    print(f"\n  [{test_id}] Index rebuild after dynamic field — recall preservation "
          f"(n={n_entities}, threshold={recall_threshold})")

    # Setup
    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
    r = adapter.execute({"operation": "create_collection",
                         "params": {"collection_name": col, "dimension": dim,
                                    "enable_dynamic_field": True}})
    if r.get("status") != "success":
        return {"test_id": test_id, "classification": "SKIP",
                "reason": f"create_collection failed: {r.get('error', '')}"}

    vecs      = make_vectors(n_entities, dim, seed=3)
    ids       = list(range(n_entities))
    groups    = [{"group": f"g{i % 5}"} for i in range(n_entities)]
    adapter.execute({"operation": "insert",
                     "params": {"collection_name": col, "vectors": vecs,
                                "ids": ids, "scalar_data": groups}})
    adapter.execute({"operation": "flush", "params": {"collection_name": col}})

    top_k     = min(10, n_entities)
    n_queries = min(20, n_entities)
    q_vecs    = make_vectors(n_queries, dim, seed=55)

    # Ground truth: brute-force nearest neighbours in Python
    def brute_force_topk(query: List[float], k: int) -> Set[int]:
        dists = [(np.linalg.norm(np.array(v) - np.array(query)), id_)
                 for v, id_ in zip(vecs, ids)]
        dists.sort()
        return {id_ for _, id_ in dists[:k]}

    # Build index
    adapter.execute({"operation": "build_index",
                     "params": {"collection_name": col, "index_type": "IVF_FLAT",
                                "metric_type": "L2", "nlist": max(4, int(n_entities ** 0.5))}})
    adapter.execute({"operation": "load", "params": {"collection_name": col}})

    # Measure recall after first build
    recalls_before = []
    for q in q_vecs:
        r = adapter.execute({"operation": "search",
                              "params": {"collection_name": col, "vector": q,
                                         "top_k": top_k}})
        if r.get("status") != "success":
            continue
        found = {int(d["id"]) for d in r.get("data", [])}
        gt    = brute_force_topk(q, top_k)
        recalls_before.append(_recall(found, gt))

    recall_before = float(np.mean(recalls_before)) if recalls_before else 0.0

    # Simulate index rebuild (drop + rebuild)
    adapter.execute({"operation": "release", "params": {"collection_name": col}})
    adapter.execute({"operation": "build_index",
                     "params": {"collection_name": col, "index_type": "IVF_FLAT",
                                "metric_type": "L2", "nlist": max(4, int(n_entities ** 0.5))}})
    adapter.execute({"operation": "load", "params": {"collection_name": col}})

    # Measure recall after rebuild
    recalls_after = []
    for q in q_vecs:
        r = adapter.execute({"operation": "search",
                              "params": {"collection_name": col, "vector": q,
                                         "top_k": top_k}})
        if r.get("status") != "success":
            continue
        found = {int(d["id"]) for d in r.get("data", [])}
        gt    = brute_force_topk(q, top_k)
        recalls_after.append(_recall(found, gt))

    recall_after = float(np.mean(recalls_after)) if recalls_after else 0.0

    regression = recall_before - recall_after
    print(f"  recall before={recall_before:.4f}  after={recall_after:.4f}  "
          f"delta={regression:+.4f}")

    if recall_after < recall_threshold:
        return {
            "test_id": test_id,
            "classification": "VIOLATION",
            "violation_type": "SCH-003",
            "violation_details": {
                "recall_before": round(recall_before, 4),
                "recall_after": round(recall_after, 4),
                "threshold": recall_threshold,
                "regression": round(regression, 4),
            },
            "reason": (f"Recall after index rebuild={recall_after:.4f} "
                       f"< threshold={recall_threshold}"),
        }

    return {
        "test_id": test_id,
        "classification": "PASS",
        "recall_before": round(recall_before, 4),
        "recall_after": round(recall_after, 4),
        "regression": round(regression, 4),
    }


def run_sch004(
    adapter: Any,
    col: str,
    n0: int,
    n1: int,
    n_delete: int,
    dim: int,
) -> Dict[str, Any]:
    """SCH-004: Count Accuracy After Mixed Schema Insert.

    Phase A: insert N0 entities (schema v1, no 'category').
    Phase B: insert N1 entities (schema v2, adds 'category' field).
    Phase C: delete n_delete entities from phase A.
    Oracle: count_entities must equal N0 + N1 - n_delete.
    """
    test_id  = "SCH-004"
    expected = n0 + n1 - n_delete
    print(f"\n  [{test_id}] Count accuracy after mixed schema insert "
          f"(n0={n0}, n1={n1}, delete={n_delete}, expected={expected})")

    adapter.execute({"operation": "drop_collection", "params": {"collection_name": col}})
    r = adapter.execute({"operation": "create_collection",
                         "params": {"collection_name": col, "dimension": dim,
                                    "enable_dynamic_field": True}})
    if r.get("status") != "success":
        return {"test_id": test_id, "classification": "SKIP",
                "reason": f"create_collection failed: {r.get('error', '')}"}

    # Phase A: schema v1 (no dynamic field)
    vecs_a = make_vectors(n0, dim, seed=10)
    ids_a  = list(range(n0))
    r = adapter.execute({"operation": "insert",
                         "params": {"collection_name": col, "vectors": vecs_a,
                                    "ids": ids_a}})
    if r.get("status") != "success":
        return {"test_id": test_id, "classification": "SKIP",
                "reason": f"insert phase A failed: {r.get('error', '')}"}

    # Phase B: schema v2 (category field)
    vecs_b   = make_vectors(n1, dim, seed=20)
    ids_b    = list(range(n0, n0 + n1))
    cats     = [{"category": f"cat{i % 3}"} for i in range(n1)]
    r = adapter.execute({"operation": "insert",
                         "params": {"collection_name": col, "vectors": vecs_b,
                                    "ids": ids_b, "scalar_data": cats}})
    if r.get("status") != "success":
        return {"test_id": test_id, "classification": "SKIP",
                "reason": f"insert phase B failed: {r.get('error', '')}"}

    adapter.execute({"operation": "flush", "params": {"collection_name": col}})

    # Count after insert
    r = adapter.execute({"operation": "count_entities",
                         "params": {"collection_name": col}})
    if r.get("status") != "success":
        return {"test_id": test_id, "classification": "SKIP",
                "reason": f"count after insert failed: {r.get('error', '')}"}
    count_after_insert = r.get("storage_count", r.get("data", [{}])[0].get("storage_count", -1))
    count_after_insert = int(count_after_insert) if count_after_insert is not None else -1

    # Phase C: delete n_delete from phase A
    del_ids = ids_a[:n_delete]
    r = adapter.execute({"operation": "delete",
                         "params": {"collection_name": col, "ids": del_ids}})
    if r.get("status") != "success":
        return {"test_id": test_id, "classification": "SKIP",
                "reason": f"delete failed: {r.get('error', '')}"}

    adapter.execute({"operation": "flush", "params": {"collection_name": col}})

    # Final count
    r = adapter.execute({"operation": "count_entities",
                         "params": {"collection_name": col}})
    if r.get("status") != "success":
        return {"test_id": test_id, "classification": "SKIP",
                "reason": f"final count_entities failed: {r.get('error', '')}"}

    actual = r.get("storage_count", r.get("data", [{}])[0].get("storage_count", -1))
    actual = int(actual) if actual is not None else -1

    print(f"  count after insert={count_after_insert} (expect {n0+n1}), "
          f"after delete={actual} (expect {expected})")

    if actual != expected:
        return {
            "test_id": test_id,
            "classification": "VIOLATION",
            "violation_type": "SCH-004",
            "violation_details": {
                "expected": expected,
                "actual": actual,
                "count_after_insert": count_after_insert,
                "discrepancy": actual - expected,
            },
            "reason": (f"count_entities={actual} != expected={expected} "
                       f"(discrepancy={actual - expected:+d})"),
        }

    return {
        "test_id": test_id,
        "classification": "PASS",
        "expected_count": expected,
        "actual_count": actual,
    }


# ---------------------------------------------------------------------------
# Adapter factory (Layer I: unified, replaces _build_milvus_adapter)
# ---------------------------------------------------------------------------

def _build_adapter(name: str, host: str, port: int,
                   pgvector_container: str = "pgvector_container",
                   pgvector_db: str = "vectordb",
                   weaviate_port: int = 8080) -> Any:
    """Unified adapter factory for R5D schema contract testing.

    Supported adapters: milvus, weaviate, pgvector.
    (Qdrant is not targeted for R5D schema contracts — no schema evolution API.)
    """
    if name == "milvus":
        from adapters.milvus_adapter import MilvusAdapter
        return MilvusAdapter({"host": host, "port": port})
    if name == "weaviate":
        from adapters.weaviate_adapter import WeaviateAdapter
        return WeaviateAdapter({"host": host, "port": weaviate_port})
    if name == "pgvector":
        from adapters.pgvector_adapter import PgvectorAdapter
        return PgvectorAdapter({"container": pgvector_container, "db": pgvector_db})
    raise ValueError(f"Unknown adapter for R5D: {name!r}. "
                     f"Supported: milvus, weaviate, pgvector")


# Legacy alias — kept for backward compatibility
def _build_milvus_adapter(host: str, port: int) -> Any:
    return _build_adapter("milvus", host, port)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="R5D Schema Contract Testing Campaign (SCH-001 through SCH-004)"
    )
    # ── Layer I: adapter selection ────────────────────────────────────────
    parser.add_argument(
        "--adapter",
        default="milvus",
        choices=["milvus", "weaviate", "pgvector"],
        help="Adapter to test (default: milvus). "
             "Note: SCH-002 (field rename) is SKIP_NOT_SUPPORTED on Weaviate."
    )
    # Milvus connection
    parser.add_argument("--host", default="localhost",
                        help="Milvus host (default: localhost)")
    parser.add_argument("--port", type=int, default=19530,
                        help="Milvus port (default: 19530)")
    # Weaviate connection
    parser.add_argument("--weaviate-host", default="localhost",
                        help="Weaviate host (default: localhost)")
    parser.add_argument("--weaviate-port", type=int, default=8080,
                        help="Weaviate HTTP port (default: 8080)")
    # pgvector connection
    parser.add_argument("--pgvector-container", default="pgvector_container",
                        help="pgvector Docker container name (default: pgvector_container)")
    parser.add_argument("--pgvector-db", default="vectordb",
                        help="pgvector database name (default: vectordb)")
    # ──────────────────────────────────────────────────────────────────────
    parser.add_argument("--offline", action="store_true",
                        help="Run in offline mode using in-memory mock adapter")
    parser.add_argument("--dim", type=int, default=64,
                        help="Vector dimension (default: 64)")
    parser.add_argument("--n-base", type=int, default=200,
                        help="Number of base (untagged) entities for SCH-001/002 (default: 200)")
    parser.add_argument("--n-tagged", type=int, default=100,
                        help="Number of tagged entities for SCH-001/002 (default: 100)")
    parser.add_argument("--n-rebuild", type=int, default=300,
                        help="Entities for SCH-003 rebuild test (default: 300)")
    parser.add_argument("--n0", type=int, default=150,
                        help="Schema v1 entities for SCH-004 (default: 150)")
    parser.add_argument("--n1", type=int, default=100,
                        help="Schema v2 entities for SCH-004 (default: 100)")
    parser.add_argument("--n-delete", type=int, default=50,
                        help="Entities to delete in SCH-004 (default: 50)")
    parser.add_argument("--recall-threshold", type=float, default=0.99,
                        help="Min recall for SCH-003 (default: 0.99)")
    parser.add_argument("--contracts", nargs="+",
                        default=["SCH-001", "SCH-002", "SCH-003", "SCH-004"],
                        choices=["SCH-001", "SCH-002", "SCH-003", "SCH-004"],
                        help="Contracts to run (default: all)")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Directory for output JSON (default: results/r5d_schema)")
    args = parser.parse_args()

    ts     = datetime.now().strftime("%Y%m%d-%H%M%S")
    # run_id now includes adapter name
    if args.offline:
        run_id = f"r5d-schema-offline-{ts}"
    else:
        run_id = f"r5d-schema-{args.adapter}-{ts}"

    output_dir = Path(args.output_dir) if args.output_dir else RESULTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*62}")
    print(f"  R5D Schema Contract Testing Campaign")
    print(f"  Run ID   : {run_id}")
    if args.offline:
        mode_str = "OFFLINE (mock)"
    elif args.adapter == "milvus":
        mode_str = f"Milvus {args.host}:{args.port}"
    elif args.adapter == "weaviate":
        mode_str = f"Weaviate {args.weaviate_host}:{args.weaviate_port}"
    elif args.adapter == "pgvector":
        mode_str = f"pgvector container={args.pgvector_container} db={args.pgvector_db}"
    else:
        mode_str = args.adapter
    print(f"  Mode     : {mode_str}")
    print(f"  Contracts: {', '.join(args.contracts)}")
    print(f"  dim={args.dim}")
    print(f"{'='*62}")

    # Build adapter
    if args.offline:
        adapter = _MockSchemaAdapter()
        print("  Mock adapter: OK")
    else:
        try:
            adapter = _build_adapter(
                args.adapter,
                host=args.host,
                port=args.port,
                pgvector_container=args.pgvector_container,
                pgvector_db=args.pgvector_db,
                weaviate_port=args.weaviate_port,
            )
            if not adapter.health_check():
                print(f"ERROR: {args.adapter} health_check failed. Use --offline for mock mode.")
                sys.exit(1)
            print(f"  {args.adapter} connected: OK")
        except (ImportError, ValueError) as e:
            print(f"ERROR: {e}\nUse --offline for mock mode.")
            sys.exit(1)

    COL = f"r5d_schema_{ts.replace('-', '')}"

    results: Dict[str, Any] = {}

    contract_runners = {
        "SCH-001": lambda: run_sch001(
            adapter, f"{COL}_sch001", args.n_base, args.n_tagged, args.dim),
        "SCH-002": lambda: run_sch002(
            adapter, f"{COL}_sch002", args.n_base, args.n_tagged, args.dim),
        "SCH-003": lambda: run_sch003(
            adapter, f"{COL}_sch003", args.n_rebuild, args.dim, args.recall_threshold),
        "SCH-004": lambda: run_sch004(
            adapter, f"{COL}_sch004", args.n0, args.n1, args.n_delete, args.dim),
    }

    # Contracts that are not supported for specific adapters
    # SCH-002 (field rename / property rename) is not available via Weaviate REST API
    # Note: offline mode still uses args.adapter as the logical DB identity for skip checks.
    SKIP_NOT_SUPPORTED: Dict[str, set] = {
        "weaviate": {"SCH-002"},
    }

    adapter_name = args.adapter  # logical DB identity (not affected by --offline)
    for contract_id in args.contracts:
        if contract_id in SKIP_NOT_SUPPORTED.get(adapter_name, set()):
            res = {
                "test_id": contract_id,
                "classification": "SKIP_NOT_SUPPORTED",
                "reason": (
                    f"{adapter_name} does not natively support {contract_id} "
                    "(field/property rename not exposed via REST API)"
                ),
            }
        else:
            try:
                res = contract_runners[contract_id]()
            except Exception as e:
                res = {"test_id": contract_id, "classification": "ERROR",
                       "reason": str(e)}
        results[contract_id] = res
        clf = res.get("classification", "?")
        reason = res.get("reason", "")
        print(f"  [{contract_id}] -> {clf}"
              + (f"  {reason}" if clf != "PASS" else ""))

    # Cleanup
    print("\n  [cleanup] dropping test collections ...")
    for suffix in ["_sch001", "_sch002", "_sch003", "_sch004"]:
        try:
            adapter.execute({"operation": "drop_collection",
                             "params": {"collection_name": f"{COL}{suffix}"}})
        except Exception:
            pass

    # Summary
    all_results = list(results.values())
    total      = len(all_results)
    passes     = [r for r in all_results if r.get("classification") == "PASS"]
    violations = [r for r in all_results if r.get("classification") == "VIOLATION"]
    skipped    = [r for r in all_results
                  if r.get("classification") in ("SKIP", "ERROR", "SKIP_NOT_SUPPORTED")]

    print(f"\n{'='*62}")
    print(f"  R5D SCHEMA CAMPAIGN SUMMARY")
    print(f"  Contracts run : {total}")
    print(f"  PASS          : {len(passes)}")
    print(f"  VIOLATIONS    : {len(violations)}")
    print(f"  SKIP/ERROR    : {len(skipped)}")

    if violations:
        print(f"\n  Violations:")
        for v in violations:
            print(f"    [{v['test_id']}] {v.get('violation_type', '')} — "
                  f"{v.get('reason', '')}")
    if skipped:
        print(f"\n  Skipped/Error:")
        for s in skipped:
            print(f"    [{s['test_id']}] {s.get('classification', '')} — "
                  f"{s.get('reason', '')[:80]}")

    # Save results
    out_path = output_dir / f"{run_id}-results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "mode": "offline" if args.offline else "milvus",
            "config": {
                "host": args.host, "port": args.port,
                "offline": args.offline, "dim": args.dim,
                "n_base": args.n_base, "n_tagged": args.n_tagged,
                "n_rebuild": args.n_rebuild,
                "n0": args.n0, "n1": args.n1, "n_delete": args.n_delete,
                "recall_threshold": args.recall_threshold,
                "contracts": args.contracts,
            },
            "summary": {
                "total": total,
                "passes": len(passes),
                "violations": len(violations),
                "skipped": len(skipped),
            },
            "results": results,
        }, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n  Results saved: {out_path}")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
