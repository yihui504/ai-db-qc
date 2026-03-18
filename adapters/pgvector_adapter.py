"""pgvector adapter for AI-DB-QC framework.

Full-featured implementation aligned with MilvusAdapter/QdrantAdapter interface
for cross-database differential testing and contract validation.

This implementation uses ONLY Python standard-library subprocess to communicate
with the pgvector Docker container via `docker exec psql`, so no psycopg2 or
other third-party PG client is required.

Operations supported:
    - create_collection
    - insert
    - insert_unique       (alias → insert)
    - search              (L2 / COSINE / IP distance via pgvector operators)
    - search_exact        (brute-force exact scan via disable_indexscan)
    - filtered_search     (SQL WHERE clause based)
    - delete
    - drop_collection
    - count_entities
    - get_collection_info
    - flush               (no-op; PostgreSQL auto-commits)
    - build_index         (NON-no-op: CREATE INDEX USING ivfflat — requires data)
    - load                (no-op; always queryable)
    - release             (no-op)
    - reload              (no-op)
    - wait                (test timing utility)

Key pgvector differences from Milvus (documented for oracle awareness):
    - Collection = PostgreSQL table; one table per collection.
    - Vector dimension is fixed at table-creation time (VECTOR(N) column type).
    - IDs are integer primary keys.
    - build_index is a real operation (IVFFlat requires data to already exist).
      This is an ALLOWED DIFFERENCE.
    - Distance operators: L2→<->, COSINE→<=>, IP→<#>

Docker start command:
    docker run -d --name pgvector -p 5432:5432 \\
      -e POSTGRES_PASSWORD=pgvector \\
      -e POSTGRES_DB=vectordb \\
      pgvector/pgvector:pg17
"""

from __future__ import annotations

import csv
import io
import math
import shlex
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

from adapters.base import AdapterBase


# ---------------------------------------------------------------------------
# Metric map
# ---------------------------------------------------------------------------

METRIC_MAP: Dict[str, str] = {
    "L2":     "<->",
    "COSINE": "<=>",
    "IP":     "<#>",
    "l2":     "<->",
    "cosine": "<=>",
    "ip":     "<#>",
    "dot":    "<#>",
}

OPS_MAP: Dict[str, str] = {
    "L2":     "vector_l2_ops",
    "COSINE": "vector_cosine_ops",
    "IP":     "vector_ip_ops",
    "l2":     "vector_l2_ops",
    "cosine": "vector_cosine_ops",
    "ip":     "vector_ip_ops",
    "dot":    "vector_ip_ops",
}


class PgvectorAdapter(AdapterBase):
    """pgvector adapter using subprocess + docker exec psql (no third-party client)."""

    def supported_operations(self) -> List[str]:
        """Return list of operations supported by PgvectorAdapter."""
        return [
            "create_collection", "insert", "insert_unique", "search", "search_exact",
            "filtered_search", "delete", "drop_collection", "count_entities",
            "get_collection_info", "flush", "build_index", "load", "release", "reload", "wait"
        ]

    def __init__(self, connection_config: Dict[str, Any]):
        self.container  = connection_config.get("container", "pgvector")
        self.user       = connection_config.get("user", "postgres")
        self.database   = connection_config.get("database", "vectordb")
        self.password   = connection_config.get("password", "pgvector")
        self.timeout    = float(connection_config.get("timeout", 60.0))
        self._table_dims: Dict[str, int] = {}
        # Ensure extension is loaded
        self._exec_sql("CREATE EXTENSION IF NOT EXISTS vector;")

    # ------------------------------------------------------------------
    # Low-level SQL execution
    # ------------------------------------------------------------------

    def _exec_sql(self, sql: str, fetch: bool = False) -> Tuple[bool, str]:
        """Execute SQL via docker exec psql.

        Returns (success, output_str).
        """
        # Write SQL to a temp file, then mount it into the container via stdin
        # Use -c flag with careful escaping; for complex SQL use heredoc approach
        # Strategy: pass SQL via docker exec stdin using -i flag
        sql_bytes = sql.encode("utf-8")

        cmd = [
            "docker", "exec", "-i", self.container,
            "bash", "-c",
            f"PGPASSWORD={self.password} psql -U {self.user} -d {self.database} "
            f"-t -A -F '|' " + ("" if not fetch else ""),
        ]

        try:
            result = subprocess.run(
                cmd,
                input=sql_bytes,
                capture_output=True,
                timeout=self.timeout,
            )
            stdout = result.stdout.decode("utf-8", errors="replace").strip()
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            if result.returncode != 0:
                # Some psql warnings go to stderr but returncode is still 0 for warnings
                if "ERROR" in stderr or "FATAL" in stderr:
                    return False, stderr
            return True, stdout
        except subprocess.TimeoutExpired:
            return False, "Timeout executing SQL"
        except Exception as e:
            return False, str(e)

    def _query(self, sql: str) -> Tuple[bool, List[List[str]]]:
        """Execute SQL and parse pipe-delimited output rows."""
        ok, raw = self._exec_sql(sql, fetch=True)
        if not ok:
            return False, []
        rows = []
        for line in raw.splitlines():
            line = line.strip()
            if line and not line.startswith("--"):
                rows.append(line.split("|"))
        return True, rows

    # ------------------------------------------------------------------
    # AdapterBase interface
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        ok, out = self._exec_sql("SELECT 1;")
        return ok and "1" in out

    def get_runtime_snapshot(self) -> Dict[str, Any]:
        snapshot = {
            "collections": [],
            "indexed_collections": [],
            "loaded_collections": [],
            "connected": False,
        }
        ok, rows = self._query(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_type='BASE TABLE';"
        )
        if ok:
            tables = [r[0] for r in rows if r]
            snapshot["collections"] = tables
            snapshot["loaded_collections"] = tables
            # Check which have vector indexes
            ok2, idx_rows = self._query(
                "SELECT tablename FROM pg_indexes "
                "WHERE indexdef ILIKE '%ivfflat%' OR indexdef ILIKE '%hnsw%';"
            )
            indexed = {r[0] for r in idx_rows if r} if ok2 else set()
            snapshot["indexed_collections"] = [t for t in tables if t in indexed]
            snapshot["connected"] = True
        return snapshot

    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        operation = request.get("operation")
        params    = request.get("params", {})
        dispatch  = {
            "create_collection":   self._create_collection,
            "insert":              self._insert,
            "insert_unique":       self._insert,
            "search":              self._search,
            "search_exact":        self._search_exact,
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
        col       = params["collection_name"]
        dimension = int(params.get("dimension", 128))
        self._table_dims[col] = dimension

        sql = (
            f'CREATE EXTENSION IF NOT EXISTS vector;\n'
            f'DROP TABLE IF EXISTS "{col}";\n'
            f'CREATE TABLE "{col}" ('
            f'id BIGINT PRIMARY KEY, '
            f'embedding vector({dimension})'
            f');'
        )
        ok, err = self._exec_sql(sql)
        if not ok:
            return {"status": "error", "error": err, "operation": "create_collection"}
        return {
            "status": "success",
            "operation": "create_collection",
            "collection_name": col,
            "data": [{"collection_name": col, "dimension": dimension}],
        }

    def _insert(self, params: Dict) -> Dict[str, Any]:
        col     = params["collection_name"]
        vectors = params.get("vectors", [])
        ids     = params.get("ids") or list(range(len(vectors)))

        if not vectors:
            return {"status": "error", "error": "No vectors provided"}

        # Convert string IDs to integers for pgvector compatibility
        ids = self._convert_ids_to_int(ids)

        # Build VALUES batch SQL
        # Chunk at 200 rows to avoid extremely long SQL
        inserted = 0
        for start in range(0, len(vectors), 200):
            chunk_vecs = vectors[start:start + 200]
            chunk_ids  = ids[start:start + 200]

            rows_sql = []
            for id_, vec in zip(chunk_ids, chunk_vecs):
                vec_str = "[" + ",".join(f"{v:.8g}" for v in vec) + "]"
                rows_sql.append(f"({int(id_)}, '{vec_str}'::vector)")

            sql = (
                f'INSERT INTO "{col}" (id, embedding) VALUES '
                + ", ".join(rows_sql)
                + " ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding;"
            )
            ok, err = self._exec_sql(sql)
            if not ok:
                return {"status": "error", "error": err, "operation": "insert"}
            inserted += len(chunk_vecs)

        return {
            "status": "success",
            "operation": "insert",
            "collection_name": col,
            "insert_count": inserted,
            "data": [{"id": id_} for id_ in ids],
        }

    def _search(self, params: Dict, exact: bool = False) -> Dict[str, Any]:
        col    = params["collection_name"]
        vector = params.get("vector") or params.get("query_vector", [])
        top_k  = int(params.get("top_k", 10))
        metric = params.get("metric_type", "L2")
        op     = METRIC_MAP.get(metric, "<->")

        vec_str = "[" + ",".join(f"{v:.8g}" for v in vector) + "]"

        # Set nprobe for IVFFlat to improve recall.
        # ALLOWED DIFFERENCE vs Milvus: Milvus has separate search params;
        # pgvector uses session-level GUC variables.
        nprobe = params.get("nprobe", 10)  # default 10 vs pgvector default 1

        disable_sql = "SET LOCAL enable_indexscan = off;\n" if exact else ""
        probe_sql   = f"SET LOCAL ivfflat.probes = {nprobe};\n" if not exact else ""
        sql = (
            f"{disable_sql}"
            f"{probe_sql}"
            f"SELECT id, embedding {op} '{vec_str}'::vector AS dist "
            f'FROM "{col}" '
            f"ORDER BY embedding {op} '{vec_str}'::vector "
            f"LIMIT {top_k};"
        )
        ok, rows = self._query(sql)
        if not ok:
            return {"status": "error", "error": str(rows), "operation": "search"}

        data = []
        for row in rows:
            if len(row) >= 2:
                try:
                    id_    = int(row[0].strip())
                    dist_f = float(row[1].strip())
                    score  = -dist_f if op == "<#>" else dist_f
                    data.append({"id": id_, "score": score, "distance": dist_f})
                except ValueError:
                    pass

        return {
            "status": "success",
            "operation": "search",
            "collection_name": col,
            "data": data,
        }

    def _search_exact(self, params: Dict) -> Dict[str, Any]:
        res = self._search(params, exact=True)
        res["operation"] = "search_exact"
        return res

    @staticmethod
    def _filter_to_sql(filter_expr: Any) -> str:
        """Convert filter expression (str or dict) to a valid SQL predicate string.

        Supports:
            str  : passed through as-is (assumed already valid SQL)
            dict : {"key": "val"}            -> key = 'val'
                   {"key": 123}              -> key = 123
                   {"key": {"gt": x}}        -> key > x
                   {"key": {"gte": x}}       -> key >= x
                   {"key": {"lt": x}}        -> key < x
                   {"key": {"lte": x}}       -> key <= x
                   multi-key dict            -> joined with AND
        Returns empty string if filter_expr is falsy.
        """
        if not filter_expr:
            return ""
        if isinstance(filter_expr, str):
            return filter_expr
        if not isinstance(filter_expr, dict):
            return ""

        op_map = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
        parts = []
        for key, val in filter_expr.items():
            col_name = key  # column name
            if isinstance(val, dict):
                # Range condition
                for range_op, range_val in val.items():
                    sql_op = op_map.get(range_op)
                    if sql_op is None:
                        continue
                    if isinstance(range_val, str):
                        parts.append(f"{col_name} {sql_op} '{range_val}'")
                    else:
                        parts.append(f"{col_name} {sql_op} {range_val}")
            elif isinstance(val, str):
                # Escape single quotes
                escaped = val.replace("'", "''")
                parts.append(f"{col_name} = '{escaped}'")
            elif isinstance(val, bool):
                parts.append(f"{col_name} = {str(val).upper()}")
            elif val is None:
                parts.append(f"{col_name} IS NULL")
            else:
                parts.append(f"{col_name} = {val}")

        return " AND ".join(parts)

    def _filtered_search(self, params: Dict) -> Dict[str, Any]:
        col         = params["collection_name"]
        vector      = params.get("vector") or params.get("query_vector", [])
        top_k       = int(params.get("top_k", 10))
        filter_expr = params.get("filter", "")
        metric      = params.get("metric_type", "L2")
        op          = METRIC_MAP.get(metric, "<->")

        vec_str = "[" + ",".join(f"{v:.8g}" for v in vector) + "]"
        # DEF-005 fix: convert dict/str filter to valid SQL predicate
        sql_predicate = self._filter_to_sql(filter_expr)
        where = f"WHERE {sql_predicate}" if sql_predicate else ""

        sql = (
            f"SELECT id, embedding {op} '{vec_str}'::vector AS dist "
            f'FROM "{col}" {where} '
            f"ORDER BY embedding {op} '{vec_str}'::vector "
            f"LIMIT {top_k};"
        )
        ok, rows = self._query(sql)
        if not ok:
            return {"status": "error", "error": str(rows), "operation": "filtered_search"}

        data = []
        for row in rows:
            if len(row) >= 2:
                try:
                    id_    = int(row[0].strip())
                    dist_f = float(row[1].strip())
                    score  = -dist_f if op == "<#>" else dist_f
                    data.append({"id": id_, "score": score, "distance": dist_f})
                except ValueError:
                    pass

        return {
            "status": "success",
            "operation": "filtered_search",
            "collection_name": col,
            "data": data,
        }

    def _delete(self, params: Dict) -> Dict[str, Any]:
        col = params["collection_name"]
        ids = params.get("ids", [])
        if not ids:
            return {"status": "error", "error": "No IDs provided"}

        # Convert string IDs to integers for pgvector compatibility
        converted_ids = self._convert_ids_to_int(ids)
        
        ids_str = ", ".join(str(int(i)) for i in converted_ids)
        sql = f'DELETE FROM "{col}" WHERE id IN ({ids_str});'
        ok, err = self._exec_sql(sql)
        if not ok:
            return {"status": "error", "error": err}
        return {
            "status": "success",
            "operation": "delete",
            "collection_name": col,
            "data": [{"deleted_ids": converted_ids}],
        }

    def _convert_ids_to_int(self, ids: List[Any]) -> List[int]:
        """Convert string IDs to integers for pgvector compatibility.
        
        pgvector uses BIGINT for IDs, but tests may pass string IDs like 'id_1'.
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

    def _drop_collection(self, params: Dict) -> Dict[str, Any]:
        col = params.get("collection_name", "")
        sql = f'DROP TABLE IF EXISTS "{col}";'
        self._exec_sql(sql)
        self._table_dims.pop(col, None)
        return {
            "status": "success",
            "operation": "drop_collection",
            "collection_name": col,
            "data": [{"deleted": True}],
        }

    def _count_entities(self, params: Dict) -> Dict[str, Any]:
        col = params["collection_name"]
        ok, rows = self._query(f'SELECT COUNT(*) FROM "{col}";')
        count = int(rows[0][0]) if ok and rows and rows[0] else 0
        return {
            "status": "success",
            "operation": "count_entities",
            "collection_name": col,
            "storage_count": count,
            "load_state": "Loaded",
            "data": [{"storage_count": count, "load_state": "Loaded"}],
        }

    def _get_collection_info(self, params: Dict) -> Dict[str, Any]:
        col = params["collection_name"]
        ok, rows = self._query(f'SELECT COUNT(*) FROM "{col}";')
        count = int(rows[0][0]) if ok and rows and rows[0] else 0
        dim = self._table_dims.get(col)
        ok2, idx_rows = self._query(
            f"SELECT indexname FROM pg_indexes "
            f"WHERE tablename = '{col}' AND "
            f"(indexdef ILIKE '%ivfflat%' OR indexdef ILIKE '%hnsw%');"
        )
        index_type = "IVFFlat/HNSW" if (ok2 and idx_rows) else "FLAT (no index)"
        return {
            "status": "success",
            "operation": "get_collection_info",
            "collection_name": col,
            "data": [{"dimension": dim, "entity_count": count,
                      "status": "Ready", "index_type": index_type}],
        }

    def _build_index(self, params: Dict) -> Dict[str, Any]:
        col            = params["collection_name"]
        index_type_raw = params.get("index_type", "IVF_FLAT").upper()
        metric         = params.get("metric_type", "L2").upper()
        ops            = OPS_MAP.get(metric, "vector_l2_ops")
        index_name     = f"{col}_embedding_idx"

        # Check row count first (IVFFlat requires data)
        ok, rows = self._query(f'SELECT COUNT(*) FROM "{col}";')
        n_rows = int(rows[0][0]) if ok and rows and rows[0] else 0

        drop_sql = f'DROP INDEX IF EXISTS "{index_name}";'
        self._exec_sql(drop_sql)

        if "HNSW" in index_type_raw:
            m  = int(params.get("m", 16))
            ef = int(params.get("ef_construction", 64))
            sql = (
                f'CREATE INDEX "{index_name}" ON "{col}" '
                f'USING hnsw (embedding {ops}) '
                f'WITH (m = {m}, ef_construction = {ef});'
            )
        else:
            if n_rows == 0:
                return {
                    "status": "error",
                    "error": "IVFFlat index requires data; table is empty. ALLOWED DIFFERENCE vs Milvus.",
                    "error_type": "AllowedDifference",
                    "operation": "build_index",
                }
            nlist = min(int(params.get("nlist", max(1, int(math.sqrt(n_rows))))), n_rows)
            sql = (
                f'CREATE INDEX "{index_name}" ON "{col}" '
                f'USING ivfflat (embedding {ops}) '
                f'WITH (lists = {nlist});'
            )

        ok, err = self._exec_sql(sql)
        if not ok:
            return {"status": "error", "error": err, "operation": "build_index"}
        return {
            "status": "success",
            "operation": "build_index",
            "collection_name": col,
            "index_type": index_type_raw,
            "data": [{"index_name": index_name, "note": "pgvector build_index is real (non-no-op)"}],
        }

    # ------------------------------------------------------------------
    # No-op operations
    # ------------------------------------------------------------------

    def _flush(self, params: Dict) -> Dict[str, Any]:
        return {"status": "success", "operation": "flush",
                "collection_name": params.get("collection_name", ""),
                "data": [{"note": "pgvector uses PG transactions (no flush needed)"}]}

    def _load(self, params: Dict) -> Dict[str, Any]:
        return {"status": "success", "operation": "load",
                "collection_name": params.get("collection_name", ""),
                "data": [{"note": "pgvector tables always queryable"}]}

    def _release(self, params: Dict) -> Dict[str, Any]:
        return {"status": "success", "operation": "release",
                "collection_name": params.get("collection_name", ""),
                "load_state": "Loaded",
                "data": [{"note": "pgvector has no release operation"}]}

    def _reload(self, params: Dict) -> Dict[str, Any]:
        return {"status": "success", "operation": "reload",
                "collection_name": params.get("collection_name", ""),
                "load_state": "Loaded",
                "data": [{"note": "pgvector always loaded"}]}

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
        pass  # No persistent connection
