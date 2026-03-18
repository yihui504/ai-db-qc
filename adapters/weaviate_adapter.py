"""Weaviate v4 adapter for AI-DB-QC framework.

Full-featured implementation aligned with MilvusAdapter/QdrantAdapter interface
for cross-database differential testing and contract validation.

This implementation uses ONLY Python standard-library urllib (no weaviate-client
package required), calling the Weaviate v1 REST API directly.

Operations supported:
    - create_collection
    - insert
    - insert_unique      (alias → insert)
    - search             (accepts 'vector' and 'query_vector' keys)
    - search_exact       (alias → search)
    - filtered_search    (Weaviate WHERE-filter based)
    - delete
    - drop_collection
    - count_entities
    - get_collection_info
    - flush              (no-op; Weaviate writes are immediately durable)
    - build_index        (no-op; Weaviate auto-manages HNSW)
    - load               (no-op; Weaviate always serves queries)
    - release            (no-op)
    - reload             (no-op)
    - wait               (test timing utility)

Key Weaviate differences from Milvus (documented for oracle awareness):
    - Collection names MUST start with an uppercase letter (handled internally).
    - UUIDs are used as point IDs; integer IDs are deterministically mapped to
      uuid5(NAMESPACE_DNS, str(id)) so they are reproducible.
    - No explicit index build / load cycle; Weaviate manages this automatically.
    - Default metric is cosine; Milvus default is L2.

Docker start command:
    docker run -d --name weaviate -p 8080:8080 -p 50051:50051 \\
      -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \\
      -e PERSISTENCE_DATA_PATH=/var/lib/weaviate \\
      cr.weaviate.io/semitechnologies/weaviate:1.36.5
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from adapters.base import AdapterBase


# ---------------------------------------------------------------------------
# Metric map: our canonical names → Weaviate distance strings
# ---------------------------------------------------------------------------

METRIC_MAP: Dict[str, str] = {
    "COSINE": "cosine",
    "L2":     "l2-squared",
    "IP":     "dot",
    "cosine": "cosine",
    "l2":     "l2-squared",
    "ip":     "dot",
    "dot":    "dot",
}


class WeaviateAdapter(AdapterBase):
    """Weaviate adapter using urllib REST (no third-party client required)."""

    def supported_operations(self) -> List[str]:
        """Return list of operations supported by WeaviateAdapter."""
        return [
            "create_collection", "insert", "insert_unique", "search", "search_exact",
            "filtered_search", "delete", "drop_collection", "count_entities",
            "get_collection_info", "flush", "build_index", "load", "release", "reload", "wait"
        ]

    def __init__(self, connection_config: Dict[str, Any]):
        self.host    = connection_config.get("host", "localhost")
        self.port    = int(connection_config.get("port", 8080))
        self.timeout = float(connection_config.get("timeout", 30.0))
        self._base   = f"http://{self.host}:{self.port}/v1"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _name(self, name: str) -> str:
        """Weaviate class names must start with uppercase."""
        if not name:
            return name
        return name[0].upper() + name[1:]

    @staticmethod
    def _int_to_uuid(id_: int) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(id_)))

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Any] = None,
        expect_codes: tuple = (200, 201, 204),
    ) -> Any:
        url = self._base + path
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                if raw:
                    return json.loads(raw)
                return {}
        except HTTPError as e:
            raw = e.read()
            try:
                msg = json.loads(raw)
            except Exception:
                msg = raw.decode(errors="replace")
            raise RuntimeError(f"HTTP {e.code} {method} {path}: {msg}") from e

    # ------------------------------------------------------------------
    # AdapterBase interface
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        try:
            res = self._request("GET", "/nodes")
            return bool(res)
        except Exception:
            return False

    def get_runtime_snapshot(self) -> Dict[str, Any]:
        snapshot = {
            "collections": [],
            "indexed_collections": [],
            "loaded_collections": [],
            "connected": False,
        }
        try:
            res = self._request("GET", "/schema")
            classes = res.get("classes", [])
            names = [c["class"] for c in classes]
            snapshot["collections"]         = names
            snapshot["indexed_collections"] = names
            snapshot["loaded_collections"]  = names
            snapshot["connected"]           = True
        except Exception:
            pass
        return snapshot

    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        operation = request.get("operation")
        params    = request.get("params", {})
        dispatch  = {
            "create_collection":   self._create_collection,
            "insert":              self._insert,
            "insert_unique":       self._insert,
            "search":              self._search,
            "search_exact":        self._search,
            "filtered_search":     self._filtered_search,
            "delete":              self._delete,
            "drop_collection":     self._drop_collection,
            "count_entities":      self._count_entities,
            "get_collection_info": self._get_collection_info,
            "flush":               self._flush,
            "build_index":         self._build_index,
            "load":                self._load,
            "release":             self._release,
            "reload":              self._reload,
            "wait":                self._wait,
        }
        handler = dispatch.get(operation)
        if handler is None:
            return {"status": "error", "error": f"Unknown operation: {operation}"}
        try:
            return handler(params)
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "operation": operation,
            }

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def _create_collection(self, params: Dict) -> Dict[str, Any]:
        col     = params["collection_name"]
        wv_name = self._name(col)
        metric  = METRIC_MAP.get(params.get("metric_type", "L2"), "l2-squared")

        # Idempotent: delete if exists
        try:
            self._request("DELETE", f"/schema/{wv_name}")
        except Exception:
            pass

        schema_body = {
            "class":       wv_name,
            "vectorizer":  "none",
            "vectorIndexConfig": {"distance": metric},
            "properties":  [
                {"name": "_orig_id", "dataType": ["int"]},
            ],
        }
        self._request("POST", "/schema", schema_body)
        return {
            "status": "success",
            "operation": "create_collection",
            "collection_name": col,
            "data": [{"collection_name": col, "weaviate_class": wv_name}],
        }

    def _ensure_properties(self, wv_name: str, props: Dict[str, Any]) -> None:
        """DEF-007 fix: ensure all property keys in *props* are registered in the
        Weaviate class schema before inserting.  Unknown properties cause GraphQL
        filtered_search to silently return empty results.

        Property type inference:
            bool  -> boolean
            int   -> int
            float -> number
            else  -> text
        """
        # Fetch existing property names from schema
        try:
            schema = self._request("GET", f"/schema/{wv_name}")
            existing = {p["name"] for p in schema.get("properties", [])}
        except Exception:
            existing = set()

        datatype_map: Dict[str, str] = {}
        for key, val in props.items():
            if key == "_orig_id" or key in existing:
                continue
            if isinstance(val, bool):
                datatype_map[key] = "boolean"
            elif isinstance(val, int):
                datatype_map[key] = "int"
            elif isinstance(val, float):
                datatype_map[key] = "number"
            else:
                datatype_map[key] = "text"

        for prop_name, wv_type in datatype_map.items():
            try:
                self._request(
                    "POST",
                    f"/schema/{wv_name}/properties",
                    {"name": prop_name, "dataType": [wv_type]},
                )
                existing.add(prop_name)
            except Exception:
                pass

    def _insert(self, params: Dict) -> Dict[str, Any]:
        col        = params["collection_name"]
        wv_name    = self._name(col)
        vectors    = params.get("vectors", [])
        ids        = params.get("ids") or list(range(len(vectors)))
        scalar     = params.get("scalar_data", [])

        if not vectors:
            return {"status": "error", "error": "No vectors provided"}

        # Convert string IDs to integers for Weaviate compatibility
        ids = self._convert_ids_to_int(ids)

        # DEF-007 fix: register any unknown scalar properties in the Weaviate schema
        # before batching so that filtered_search WHERE clauses can find them.
        if scalar:
            # Collect the union of all property keys across scalar records
            all_keys: Dict[str, Any] = {}
            for s in scalar:
                if isinstance(s, dict):
                    all_keys.update(s)
            if all_keys:
                self._ensure_properties(wv_name, all_keys)

        # Batch insert via /batch/objects
        objects = []
        for i, (vec, id_) in enumerate(zip(vectors, ids)):
            props: Dict[str, Any] = {"_orig_id": int(id_)}
            if scalar and i < len(scalar):
                props.update(scalar[i])
            objects.append({
                "class":      wv_name,
                "id":         self._int_to_uuid(int(id_)),
                "vector":     list(vec),
                "properties": props,
            })

        # Weaviate batch max ~1000; chunk at 500
        inserted = 0
        for start in range(0, len(objects), 500):
            chunk = objects[start:start + 500]
            res = self._request("POST", "/batch/objects", {"objects": chunk})
            # res is a list; each item has "result" with "status"
            if isinstance(res, list):
                inserted += sum(
                    1 for o in res
                    if isinstance(o, dict) and o.get("result", {}).get("status") == "SUCCESS"
                )
            else:
                inserted += len(chunk)

        return {
            "status": "success",
            "operation": "insert",
            "collection_name": col,
            "insert_count": inserted,
            "data": [{"id": id_} for id_ in ids],
        }

    def _convert_ids_to_int(self, ids: List[Any]) -> List[int]:
        """Convert string IDs to integers for Weaviate compatibility.
        
        Weaviate uses UUIDs internally but accepts integer IDs, 
        but tests may pass string IDs like 'id_1'.
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
        col     = params["collection_name"]
        wv_name = self._name(col)
        vector  = params.get("vector") or params.get("query_vector", [])
        top_k   = int(params.get("top_k", 10))

        gql = """
{
  Get {
    %s(
      limit: %d
      nearVector: { vector: %s }
    ) {
      _orig_id
      _additional { id distance }
    }
  }
}
""" % (wv_name, top_k, json.dumps(list(vector)))

        res = self._request("POST", "/graphql", {"query": gql})
        objects = (
            res.get("data", {}).get("Get", {}).get(wv_name, []) or []
        )
        data = []
        for obj in objects:
            orig_id = obj.get("_orig_id")
            if orig_id is None:
                wv_uuid = (obj.get("_additional") or {}).get("id", "0")
                orig_id = uuid.UUID(wv_uuid).int % (2 ** 53) if wv_uuid else 0
            dist = (obj.get("_additional") or {}).get("distance", 0.0) or 0.0
            data.append({"id": int(orig_id), "score": float(dist), "distance": float(dist)})

        return {
            "status": "success",
            "operation": "search",
            "collection_name": col,
            "data": data,
        }

    def _filtered_search(self, params: Dict) -> Dict[str, Any]:
        col         = params["collection_name"]
        wv_name     = self._name(col)
        vector      = params.get("vector") or params.get("query_vector", [])
        top_k       = int(params.get("top_k", 10))
        filter_expr = params.get("filter", {})

        # Build simple where clause
        where_gql = self._build_where_gql(filter_expr)

        if where_gql:
            gql = """
{
  Get {
    %s(
      limit: %d
      nearVector: { vector: %s }
      where: %s
    ) {
      _orig_id
      _additional { id distance }
    }
  }
}
""" % (wv_name, top_k, json.dumps(list(vector)), where_gql)
        else:
            # Fallback to unfiltered if we can't parse the filter
            return self._search(params)

        res = self._request("POST", "/graphql", {"query": gql})
        objects = res.get("data", {}).get("Get", {}).get(wv_name, []) or []
        data = []
        for obj in objects:
            orig_id = obj.get("_orig_id")
            if orig_id is None:
                wv_uuid = (obj.get("_additional") or {}).get("id", "0")
                orig_id = uuid.UUID(wv_uuid).int % (2 ** 53) if wv_uuid else 0
            dist = (obj.get("_additional") or {}).get("distance", 0.0) or 0.0
            data.append({"id": int(orig_id), "score": float(dist), "distance": float(dist)})

        return {
            "status": "success",
            "operation": "filtered_search",
            "collection_name": col,
            "data": data,
        }

    def _build_where_gql(self, filter_expr: Any) -> Optional[str]:
        """Convert filter to Weaviate GraphQL where string."""
        import re
        if not filter_expr:
            return None
        if isinstance(filter_expr, str):
            m = re.match(r'(\w+)\s*==\s*[\'"](.+)[\'"]', filter_expr.strip())
            if m:
                key, val = m.group(1), m.group(2)
                return '{ path: ["%s"] operator: Equal valueText: "%s" }' % (key, val)
            return None
        if isinstance(filter_expr, dict):
            conditions = []
            for key, val in filter_expr.items():
                if isinstance(val, (list, tuple)):
                    sub = " ".join(
                        '{ path: ["%s"] operator: Equal valueText: "%s" }' % (key, v)
                        for v in val
                    )
                    conditions.append("{ operator: Or operands: [%s] }" % sub)
                elif isinstance(val, bool):
                    conditions.append(
                        '{ path: ["%s"] operator: Equal valueBoolean: %s }' % (key, str(val).lower())
                    )
                elif isinstance(val, int):
                    conditions.append(
                        '{ path: ["%s"] operator: Equal valueInt: %d }' % (key, val)
                    )
                elif isinstance(val, float):
                    conditions.append(
                        '{ path: ["%s"] operator: Equal valueNumber: %g }' % (key, val)
                    )
                else:
                    conditions.append(
                        '{ path: ["%s"] operator: Equal valueText: "%s" }' % (key, val)
                    )
            if not conditions:
                return None
            if len(conditions) == 1:
                return conditions[0]
            return "{ operator: And operands: [%s] }" % " ".join(conditions)
        return None

    def _delete(self, params: Dict) -> Dict[str, Any]:
        col     = params["collection_name"]
        wv_name = self._name(col)
        ids     = params.get("ids", [])

        # Convert string IDs to integers for Weaviate compatibility
        converted_ids = self._convert_ids_to_int(ids)

        deleted = 0
        for id_ in converted_ids:
            wv_uuid = self._int_to_uuid(int(id_))
            try:
                self._request("DELETE", f"/objects/{wv_name}/{wv_uuid}")
                deleted += 1
            except Exception:
                pass

        return {
            "status": "success",
            "operation": "delete",
            "collection_name": col,
            "delete_count": deleted,
            "data": [{"deleted_ids": converted_ids}],
        }

    def _drop_collection(self, params: Dict) -> Dict[str, Any]:
        col     = params.get("collection_name", "")
        wv_name = self._name(col)
        try:
            self._request("DELETE", f"/schema/{wv_name}")
        except Exception:
            pass
        return {
            "status": "success",
            "operation": "drop_collection",
            "collection_name": col,
            "data": [{"deleted": True}],
        }

    def _count_entities(self, params: Dict) -> Dict[str, Any]:
        col     = params["collection_name"]
        wv_name = self._name(col)

        gql = '{ Aggregate { %s { meta { count } } } }' % wv_name
        try:
            res = self._request("POST", "/graphql", {"query": gql})
            count = (
                res.get("data", {}).get("Aggregate", {}).get(wv_name, [{}])[0]
                .get("meta", {}).get("count", 0)
            )
        except Exception:
            count = 0

        return {
            "status": "success",
            "operation": "count_entities",
            "collection_name": col,
            "storage_count": count,
            "load_state": "Loaded",
            "data": [{"storage_count": count, "load_state": "Loaded"}],
        }

    def _get_collection_info(self, params: Dict) -> Dict[str, Any]:
        col     = params["collection_name"]
        wv_name = self._name(col)
        try:
            schema = self._request("GET", f"/schema/{wv_name}")
        except Exception:
            schema = {}
        gql = '{ Aggregate { %s { meta { count } } } }' % wv_name
        try:
            res = self._request("POST", "/graphql", {"query": gql})
            count = (
                res.get("data", {}).get("Aggregate", {}).get(wv_name, [{}])[0]
                .get("meta", {}).get("count", 0)
            )
        except Exception:
            count = 0
        return {
            "status": "success",
            "operation": "get_collection_info",
            "collection_name": col,
            "data": [{
                "entity_count": count,
                "status": "Ready",
                "index_type": "HNSW",
                "weaviate_class": wv_name,
                "schema": schema,
            }],
        }

    # ------------------------------------------------------------------
    # No-op operations
    # ------------------------------------------------------------------

    def _flush(self, params: Dict) -> Dict[str, Any]:
        return {"status": "success", "operation": "flush",
                "collection_name": params.get("collection_name", ""),
                "data": [{"note": "Weaviate writes are immediately durable"}]}

    def _build_index(self, params: Dict) -> Dict[str, Any]:
        return {"status": "success", "operation": "build_index",
                "collection_name": params.get("collection_name", ""),
                "data": [{"note": "Weaviate auto-builds HNSW index"}]}

    def _load(self, params: Dict) -> Dict[str, Any]:
        return {"status": "success", "operation": "load",
                "collection_name": params.get("collection_name", ""),
                "data": [{"note": "Weaviate collections always loaded"}]}

    def _release(self, params: Dict) -> Dict[str, Any]:
        return {"status": "success", "operation": "release",
                "collection_name": params.get("collection_name", ""),
                "load_state": "Loaded",
                "data": [{"note": "Weaviate has no release operation"}]}

    def _reload(self, params: Dict) -> Dict[str, Any]:
        return {"status": "success", "operation": "reload",
                "collection_name": params.get("collection_name", ""),
                "load_state": "Loaded",
                "data": [{"note": "Weaviate always loaded"}]}

    def _wait(self, params: Dict) -> Dict[str, Any]:
        ms = int(params.get("duration_ms", 0))
        start = time.time()
        time.sleep(ms / 1000.0)
        elapsed = int((time.time() - start) * 1000)
        return {
            "status": "success",
            "operation": "wait",
            "duration_ms_requested": ms,
            "duration_ms_actual": elapsed,
            "data": [{"waited_ms": elapsed}],
        }

    def close(self) -> None:
        pass  # No persistent connection to close
