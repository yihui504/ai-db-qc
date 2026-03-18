"""Qdrant adapter for AI-DB-QC framework.

Full-featured implementation aligned with MilvusAdapter interface for
cross-database differential testing and contract validation.

Operations supported:
    - create_collection
    - insert
    - search            (accepts both 'vector' and 'query_vector' keys)
    - filtered_search   (payload-filter based; aligns with Milvus filtered_search)
    - delete
    - drop_collection
    - count_entities
    - get_collection_info
    - flush             (no-op; Qdrant writes are immediately durable)
    - build_index       (no-op; Qdrant auto-builds HNSW)
    - load              (no-op; Qdrant auto-loads collections)

Key Qdrant differences from Milvus (documented for oracle awareness):
    - Auto-HNSW index, no explicit build_index
    - In-memory by default, no explicit load
    - Uses payload (JSON metadata) instead of schema-defined scalar fields
    - Integer / UUID IDs only (no auto-increment like Milvus)
    - Default metric is COSINE; Milvus default is L2
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from qdrant_client import QdrantClient, models
    from qdrant_client.http import models as rest_models
except ImportError:
    raise ImportError(
        "qdrant-client not installed. Install with: pip install qdrant-client"
    )

from adapters.base import AdapterBase


class QdrantAdapter(AdapterBase):
    """Qdrant adapter aligned with MilvusAdapter interface for differential testing.

    Design goals:
    1. Same operation names as MilvusAdapter
    2. Normalised output shapes so oracles can compare results generically
    3. Explicit documentation of semantic differences (not bugs — allowed differences)
    """

    def supported_operations(self) -> List[str]:
        """Return list of operations supported by QdrantAdapter."""
        return [
            "create_collection", "insert", "search", "filtered_search",
            "delete", "drop_collection", "count_entities", "get_collection_info",
            "flush", "build_index", "load"
        ]

    METRIC_MAP = {
        "COSINE": models.Distance.COSINE,
        "L2":     models.Distance.EUCLID,
        "IP":     models.Distance.DOT,
        # Milvus-style aliases
        "cosine": models.Distance.COSINE,
        "l2":     models.Distance.EUCLID,
        "ip":     models.Distance.DOT,
        "dot":    models.Distance.DOT,
    }

    def __init__(self, connection_config: Dict[str, Any]):
        """Initialise Qdrant adapter.

        Args:
            connection_config:
                url  (str):   Qdrant base URL, default "http://localhost:6333"
                timeout (float): Request timeout, default 30.0
                api_key (str, optional): API key for Qdrant Cloud
        """
        self.url     = connection_config.get("url", "http://localhost:6333")
        self.timeout = float(connection_config.get("timeout", 30.0))
        self.api_key = connection_config.get("api_key")
        self._client: Optional[QdrantClient] = None
        self._connect()

    # ─────────────────────────────────────────────────────────────
    # Connection
    # ─────────────────────────────────────────────────────────────

    def _connect(self) -> None:
        kwargs: Dict[str, Any] = {"url": self.url, "timeout": self.timeout}
        if self.api_key:
            kwargs["api_key"] = self.api_key
        self._client = QdrantClient(**kwargs)

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._connect()
        return self._client

    def health_check(self) -> bool:
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    # ─────────────────────────────────────────────────────────────
    # Dispatch
    # ─────────────────────────────────────────────────────────────

    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        operation = request.get("operation")
        params    = request.get("params", {})

        try:
            dispatch = {
                "create_collection":  self._create_collection,
                "insert":             self._insert,
                "insert_unique":      self._insert,
                "search":             self._search,
                "search_exact":       self._search,
                "filtered_search":    self._filtered_search,
                "delete":             self._delete,
                "drop_collection":    self._drop_collection,
                "count_entities":     self._count_entities,
                "get_collection_info": self._get_collection_info,
                "flush":              self._flush,
                "build_index":        self._build_index,
                "load":               self._load,
                "release":            self._release,
                "reload":             self._reload,
                "wait":               self._wait,
            }
            handler = dispatch.get(operation)
            if handler is None:
                return {
                    "status": "error",
                    "error": f"Unknown operation: {operation}",
                    "error_type": "ValueError",
                }
            return handler(params)
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "operation": operation,
            }

    # ─────────────────────────────────────────────────────────────
    # Core operations
    # ─────────────────────────────────────────────────────────────

    def _create_collection(self, params: Dict) -> Dict[str, Any]:
        """Create a Qdrant collection.

        Allowed-difference note vs Milvus:
          - Qdrant default metric is COSINE; Milvus default is L2.
          - Schema is schemaless (no explicit field declaration needed).
        """
        collection_name = params["collection_name"]
        dimension       = int(params.get("dimension", 128))
        metric_type     = params.get("metric_type", "L2")
        distance        = self.METRIC_MAP.get(metric_type, models.Distance.EUCLID)

        # Drop if already exists (idempotent create)
        try:
            existing = [c.name for c in self.client.get_collections().collections]
            if collection_name in existing:
                self.client.delete_collection(collection_name)
        except Exception:
            pass

        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=dimension, distance=distance),
        )

        return {
            "status": "success",
            "operation": "create_collection",
            "collection_name": collection_name,
            "data": [{
                "collection_name": collection_name,
                "dimension": dimension,
                "metric_type": metric_type,
                "distance": str(distance),
            }],
        }

    def _insert(self, params: Dict) -> Dict[str, Any]:
        """Upsert vectors.

        Qdrant requires integer or UUID IDs.  If caller doesn't supply IDs,
        sequential integers starting at 0 are generated.

        Scalar data is stored as Qdrant 'payload' (JSON dict per point).

        Allowed-difference note:
          - Milvus: IDs are defined at schema level (INT64 primary key).
          - Qdrant: IDs are per-point, no schema required.
        """
        collection_name = params["collection_name"]
        vectors         = params.get("vectors", [])
        ids             = params.get("ids")
        scalar_data     = params.get("scalar_data", [])
        payload_global  = params.get("payload", {})

        if not vectors:
            return {"status": "error", "error": "No vectors provided", "operation": "insert"}

        # Resolve IDs and convert string IDs to integers
        if ids is None:
            ids = list(range(len(vectors)))
        else:
            ids = self._convert_ids_to_int(ids)

        # Build points
        points = []
        for i, (vec, id_) in enumerate(zip(vectors, ids)):
            # Merge per-entity scalar data with global payload
            payload: Dict[str, Any] = dict(payload_global)
            if scalar_data and i < len(scalar_data):
                payload.update(scalar_data[i])
            points.append(models.PointStruct(id=id_, vector=list(vec), payload=payload))

        # Upsert in batches to avoid request timeouts
        batch_size = 500
        for i in range(0, len(points), batch_size):
            self.client.upsert(
                collection_name=collection_name,
                points=points[i:i + batch_size],
            )

        return {
            "status": "success",
            "operation": "insert",
            "collection_name": collection_name,
            "insert_count": len(points),
            "data": [{"id": p.id} for p in points],
        }

    def _convert_ids_to_int(self, ids: List[Any]) -> List[int]:
        """Convert string IDs to integers for Qdrant compatibility.
        
        Qdrant requires integer or UUID IDs, but tests may pass string IDs like 'id_1'.
        This method extracts numeric portion or generates deterministic integers.
        
        Args:
            ids: List of IDs (strings or integers)
            
        Returns:
            List of integer IDs
        """
        converted = []
        for id_val in ids:
            if isinstance(id_val, int):
                converted.append(id_val)
            elif isinstance(id_val, str):
                # Try to extract numeric portion from strings like 'id_1', 'entity_2'
                import re
                numeric_match = re.search(r'\d+', id_val)
                if numeric_match:
                    converted.append(int(numeric_match.group()))
                else:
                    # Fallback: use hash for deterministic integer
                    converted.append(abs(hash(id_val)) % (2**63))
            else:
                # Try direct conversion
                converted.append(int(id_val))
        return converted

    def _search(self, params: Dict) -> Dict[str, Any]:
        """Search for nearest neighbours.

        Accepts either 'vector' (Milvus-style key) or 'query_vector' (Qdrant-style).
        Output shape matches MilvusAdapter._search() for oracle compatibility:
            [{"id": ..., "score": ..., "distance": ...}, ...]
        """
        collection_name = params["collection_name"]
        # Accept both naming conventions
        vector  = params.get("vector") or params.get("query_vector", [])
        top_k   = int(params.get("top_k", 10))
        # Optional ef (search-time HNSW parameter)
        search_params = None
        ef = params.get("ef")
        if ef is not None:
            search_params = models.SearchParams(hnsw_ef=int(ef), exact=False)

        if isinstance(vector, str):
            import ast
            vector = ast.literal_eval(vector)

        results = self.client.search(
            collection_name=collection_name,
            query_vector=list(vector),
            limit=top_k,
            search_params=search_params,
        )

        formatted = [
            {
                "id":       r.id,
                "score":    r.score,
                "distance": r.score,          # Qdrant score = distance for EUCLID
                "payload":  r.payload or {},
            }
            for r in results
        ]

        return {
            "status": "success",
            "operation": "search",
            "collection_name": collection_name,
            "data": formatted,
        }

    def _filtered_search(self, params: Dict) -> Dict[str, Any]:
        """Search with payload filter.

        Translates the same filter dict format used by MilvusAdapter._filtered_search()
        into a Qdrant payload filter (FieldCondition + MatchValue).

        Supported filter dict formats:
            {"color": "red"}             -> must match color == "red"
            {"status": ["active", "new"]}-> must match status in [active, new]
            {"score": None}              -> must_not have field (null-check)
            {"score": {"gt": 10}}       -> range: score > 10
            {"score": {"gte": 10, "lte": 100}} -> range: 10 <= score <= 100
            {"date": {"gte": "2024-01-01"}} -> datetime range

        Allowed-difference note:
          - Milvus: filter is a SQL-like expression string ("color == 'red'")
          - Qdrant: filter is a structured condition object
          Both implement pre-application before vector scoring.
        """
        collection_name = params["collection_name"]
        vector          = params.get("vector") or params.get("query_vector", [])
        top_k           = int(params.get("top_k", 10))
        filter_expr     = params.get("filter", {})

        if isinstance(vector, str):
            import ast
            vector = ast.literal_eval(vector)

        # Build Qdrant filter from dict or pass-through if already a Qdrant Filter
        qdrant_filter = None
        if filter_expr and isinstance(filter_expr, dict):
            must_conditions = []
            must_not_conditions = []
            for key, value in filter_expr.items():
                condition = self._build_filter_condition(key, value)
                if condition is None:
                    # Null check -> must NOT have the field
                    must_not_conditions.append(
                        models.FieldCondition(key=key, match=models.MatchAny(any=[]))
                    )
                elif isinstance(condition, tuple) and condition[0] == "must_not":
                    must_not_conditions.append(condition[1])
                else:
                    must_conditions.append(condition)
            qdrant_filter = models.Filter(
                must=must_conditions if must_conditions else None,
                must_not=must_not_conditions if must_not_conditions else None,
            )
        elif isinstance(filter_expr, str) and filter_expr:
            # Best-effort: parse simple "key == 'value'" expressions
            qdrant_filter = self._parse_string_filter(filter_expr)

        results = self.client.search(
            collection_name=collection_name,
            query_vector=list(vector),
            query_filter=qdrant_filter,
            limit=top_k,
        )

        formatted = [
            {
                "id":       r.id,
                "score":    r.score,
                "distance": r.score,
                "payload":  r.payload or {},
            }
            for r in results
        ]

        return {
            "status": "success",
            "operation": "filtered_search",
            "collection_name": collection_name,
            "data": formatted,
        }

    def _build_filter_condition(self, key: str, value: Any) -> Optional[models.FieldCondition]:
        """Build a Qdrant FieldCondition from a filter value.

        Supports:
            - Simple values (str, int, float, bool): MatchValue
            - Lists/sets: MatchAny
            - None: null check (return None to signal must_not)
            - Range dict: {"gt": x}, {"gte": x}, {"lt": x}, {"lte": x}, or combinations
            - Datetime strings: handled as range conditions

        Returns:
            models.FieldCondition or None (for null checks)
        """
        if value is None:
            # Null check -> signal to caller to add to must_not
            return ("must_not", None)

        if isinstance(value, (list, set)):
            return models.FieldCondition(
                key=key,
                match=models.MatchAny(any=list(value))
            )

        # Check for range specification
        if isinstance(value, dict):
            return self._build_range_condition(key, value)

        # Simple equality
        return models.FieldCondition(
            key=key,
            match=models.MatchValue(value=value)
        )

    def _build_range_condition(self, key: str, range_spec: Dict[str, Any]) -> Optional[models.FieldCondition]:
        """Build a range condition for numeric or datetime fields.

        Supports:
            {"gt": 10}       -> x > 10
            {"gte": 10}      -> x >= 10
            {"lt": 100}      -> x < 100
            {"lte": 100}     -> x <= 100
            {"gt": 10, "lt": 100} -> 10 < x < 100
            Combined with datetime strings: {"gte": "2024-01-01T00:00:00Z"}
        """
        range_conditions = []

        # DEF-006 fix: use correct Range field names (gt->gt, gte->gte, lt->lt, lte->lte)
        if "gt" in range_spec:
            range_conditions.append(
                models.Range(gt=float(range_spec["gt"]) if not isinstance(range_spec["gt"], str) else range_spec["gt"])
            )
        if "gte" in range_spec:
            range_conditions.append(
                models.Range(gte=float(range_spec["gte"]) if not isinstance(range_spec["gte"], str) else range_spec["gte"])
            )
        if "lt" in range_spec:
            range_conditions.append(
                models.Range(lt=float(range_spec["lt"]) if not isinstance(range_spec["lt"], str) else range_spec["lt"])
            )
        if "lte" in range_spec:
            range_conditions.append(
                models.Range(lte=float(range_spec["lte"]) if not isinstance(range_spec["lte"], str) else range_spec["lte"])
            )

        if range_conditions:
            # Merge into a single Range object
            merged_range = models.Range()
            for rc in range_conditions:
                if hasattr(rc, 'gt') and rc.gt is not None:
                    merged_range.gt = rc.gt
                if hasattr(rc, 'gte') and rc.gte is not None:
                    merged_range.gte = rc.gte
                if hasattr(rc, 'lt') and rc.lt is not None:
                    merged_range.lt = rc.lt
                if hasattr(rc, 'lte') and rc.lte is not None:
                    merged_range.lte = rc.lte

            return models.FieldCondition(key=key, range=merged_range)

        # Empty dict, treat as equality (fallback)
        return None

    def _parse_string_filter(self, expr: str) -> Optional[models.Filter]:
        """Best-effort parser for simple SQL-like filter expressions.

        Handles: "key == 'value'", "key in ['a', 'b']"
        Returns None if parsing fails (falls back to unfiltered search).
        """
        import re
        # Simple equality: key == 'value' or key == "value"
        m = re.match(r"(\w+)\s*==\s*['\"](.+)['\"]", expr.strip())
        if m:
            key, val = m.group(1), m.group(2)
            return models.Filter(must=[
                models.FieldCondition(key=key, match=models.MatchValue(value=val))
            ])
        return None

    def _delete(self, params: Dict) -> Dict[str, Any]:
        """Delete points by ID list."""
        collection_name = params["collection_name"]
        ids             = params.get("ids", [])

        if not ids:
            return {"status": "error", "error": "No IDs provided", "operation": "delete"}

        # Convert string IDs to integers for Qdrant compatibility
        converted_ids = self._convert_ids_to_int(ids)
        
        self.client.delete(
            collection_name=collection_name,
            points_selector=models.PointIdsList(points=converted_ids),
        )

        return {
            "status": "success",
            "operation": "delete",
            "collection_name": collection_name,
            "delete_count": len(converted_ids),
            "data": [{"deleted_ids": converted_ids}],
        }

    def _drop_collection(self, params: Dict) -> Dict[str, Any]:
        """Delete a collection (idempotent — no error if not exists)."""
        collection_name = params.get("collection_name", "")
        try:
            self.client.delete_collection(collection_name)
        except Exception:
            pass  # Treat "not found" as success for idempotent drop

        return {
            "status": "success",
            "operation": "drop_collection",
            "collection_name": collection_name,
            "data": [{"deleted": True}],
        }

    def _count_entities(self, params: Dict) -> Dict[str, Any]:
        """Count entities in a collection.

        Uses client.count() which returns exact count from Qdrant.

        Normalised output matches MilvusAdapter._count_entities():
            data[0].storage_count  -> entity count
            data[0].load_state     -> always "Loaded" (Qdrant auto-loads)
        """
        collection_name = params["collection_name"]

        count_result = self.client.count(
            collection_name=collection_name,
            exact=True,
        )
        entity_count = count_result.count

        return {
            "status": "success",
            "operation": "count_entities",
            "collection_name": collection_name,
            "storage_count": entity_count,
            "load_state": "Loaded",        # Qdrant is always loaded
            "data": [{
                "storage_count": entity_count,
                "load_state": "Loaded",
                "note": "Qdrant collections are always loaded (in-memory by default)",
            }],
        }

    def _get_collection_info(self, params: Dict) -> Dict[str, Any]:
        """Get collection metadata: vector dimension, entity count, index config."""
        collection_name = params["collection_name"]

        info = self.client.get_collection(collection_name=collection_name)

        # Extract dimension from vector config
        dimension = None
        if hasattr(info.config.params, "vectors"):
            vc = info.config.params.vectors
            if hasattr(vc, "size"):
                dimension = vc.size

        return {
            "status": "success",
            "operation": "get_collection_info",
            "collection_name": collection_name,
            "data": [{
                "dimension":      dimension,
                "entity_count":   info.points_count,
                "status":         str(info.status),
                "optimizer_status": str(info.optimizer_status),
                "index_type":     "HNSW",   # Qdrant always uses HNSW
            }],
        }

    # ─────────────────────────────────────────────────────────────
    # No-op / compatibility operations
    # ─────────────────────────────────────────────────────────────

    def _flush(self, params: Dict) -> Dict[str, Any]:
        """NO-OP: Qdrant writes are immediately durable (WAL-backed).

        Allowed-difference note:
          - Milvus requires explicit flush to persist buffered inserts.
          - Qdrant has no buffered-write model; all upserts are immediately visible.
        """
        return {
            "status": "success",
            "operation": "flush",
            "collection_name": params.get("collection_name", ""),
            "data": [{
                "flushed": True,
                "note": "Qdrant writes are immediately durable (no flush needed)",
            }],
        }

    def _build_index(self, params: Dict) -> Dict[str, Any]:
        """NO-OP: Qdrant auto-builds HNSW index on first upsert.

        Allowed-difference note:
          - Milvus: explicit index build required before load.
          - Qdrant: index is built automatically and incrementally.
        """
        return {
            "status": "success",
            "operation": "build_index",
            "collection_name": params.get("collection_name", ""),
            "index_type": "HNSW",
            "algo_params": {},
            "data": [{
                "operation": "no-op",
                "note": "Qdrant auto-creates HNSW index on upsert",
            }],
        }

    def _load(self, params: Dict) -> Dict[str, Any]:
        """NO-OP: Qdrant collections are always in-memory.

        Allowed-difference note:
          - Milvus: collection must be explicitly loaded before search.
          - Qdrant: collections are always queryable.
        """
        return {
            "status": "success",
            "operation": "load",
            "collection_name": params.get("collection_name", ""),
            "data": [{
                "operation": "no-op",
                "note": "Qdrant auto-loads collections",
            }],
        }

    def _release(self, params: Dict) -> Dict[str, Any]:
        """NO-OP: Qdrant has no concept of release/unload."""
        return {
            "status": "success",
            "operation": "release",
            "collection_name": params.get("collection_name", ""),
            "load_state": "Loaded",
            "data": [{
                "note": "Qdrant has no release operation; collections always in memory",
            }],
        }

    def _reload(self, params: Dict) -> Dict[str, Any]:
        """NO-OP: Qdrant never needs reload."""
        return {
            "status": "success",
            "operation": "reload",
            "collection_name": params.get("collection_name", ""),
            "load_state": "Loaded",
            "data": [{"note": "Qdrant always loaded; reload is a no-op"}],
        }

    def _wait(self, params: Dict) -> Dict[str, Any]:
        """Wait for specified duration (test timing utility)."""
        import time
        duration_ms = int(params.get("duration_ms", 0))
        start = time.time()
        time.sleep(duration_ms / 1000.0)
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "status": "success",
            "operation": "wait",
            "duration_ms_requested": duration_ms,
            "duration_ms_actual": elapsed_ms,
            "data": [{"waited_ms": elapsed_ms}],
        }

    # ─────────────────────────────────────────────────────────────
    # Convenience helpers (not part of AdapterBase interface)
    # ─────────────────────────────────────────────────────────────

    def get_runtime_snapshot(self) -> Dict[str, Any]:
        """Return a runtime snapshot compatible with PreconditionEvaluator."""
        snapshot = {
            "collections": [],
            "indexed_collections": [],
            "loaded_collections": [],
            "connected": True,
            "memory_stats": {},
        }
        try:
            collections = self.client.get_collections().collections
            snapshot["collections"] = [c.name for c in collections]
            # In Qdrant, all existing collections are indexed and loaded
            snapshot["indexed_collections"] = list(snapshot["collections"])
            snapshot["loaded_collections"]  = list(snapshot["collections"])
        except Exception:
            snapshot["connected"] = False
        return snapshot

    def close(self) -> None:
        """Close the client connection."""
        try:
            if self._client:
                self._client.close()
        except Exception:
            pass
