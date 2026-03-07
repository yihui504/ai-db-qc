"""Minimal seekdb adapter for AI-native database testing.

This adapter provides a thin parameter mapping layer to reuse existing
test case families with seekdb's AI-native search capabilities.

Uses MySQL-compatible SQL protocol (NOT REST API).
SQL Dialect Features:
- Vector columns: VECTOR(N)
- Vector literals: '[x, y, z]'
- Distance function: l2_distance(vector, query)
- Vector search: SELECT ... ORDER BY l2_distance(...) LIMIT k
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import pymysql

from adapters.base import AdapterBase


class SeekDBAdapter(AdapterBase):
    """Minimal adapter for seekdb AI-native search database.

    Focus: Get basic operations working with minimal complexity.
    Reuses: existing triage, oracles, evidence pipeline.

    Architecture:
    - Maps generic operations to seekdb SQL queries
    - Thin parameter mapping layer for Milvus-shaped parameters
    - Handles vector, filtered search via SQL
    """

    def __init__(
        self,
        api_endpoint: str,
        api_key: str,
        collection: str = "test_collection",
        timeout: int = 30,
        user: str = "root",
        password: str = "",
        database: str = "test"
    ):
        """Initialize seekdb adapter.

        Args:
            api_endpoint: seekdb host (e.g., "127.0.0.1:2881" or "127.0.0.1")
            api_key: Not used for SQL connection (kept for API compatibility)
            collection: Default collection (table) name
            timeout: Query timeout in seconds
            user: MySQL username
            password: MySQL password
            database: MySQL database name
        """
        # Parse host and port from api_endpoint
        if ":" in api_endpoint:
            self.host, self.port = api_endpoint.split(":")
            self.port = int(self.port)
        else:
            self.host = api_endpoint
            self.port = 2881  # Default seekdb SQL port

        self.api_key = api_key  # Not used for SQL, kept for compatibility
        self.collection = collection
        self.timeout = timeout
        self.user = user
        self.password = password
        self.database = database
        self.conn: Optional[pymysql.connections.Connection] = None

    def _get_connection(self) -> pymysql.connections.Connection:
        """Get or create MySQL connection."""
        if self.conn is None or not self.conn.open:
            self.conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
        return self.conn

    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute request against seekdb.

        Maps generic operations to seekdb SQL queries with parameter mapping.

        Args:
            request: Dict with keys:
                - operation (str): Operation name
                - params (dict): Operation parameters (Milvus-shaped)

        Returns:
            Response dict with status, data, or error
        """
        operation = request.get("operation", "")
        params = request.get("params", {})

        try:
            if operation == "search":
                return self._search(params)
            elif operation == "filtered_search":
                return self._filtered_search(params)
            elif operation == "hybrid_search":
                return self._hybrid_search(params)
            elif operation == "insert":
                return self._insert(params)
            elif operation == "delete":
                return self._delete(params)
            elif operation == "create_collection":
                return self._create_collection(params)
            elif operation == "drop_collection":
                return self._drop_collection(params)
            elif operation == "build_index":
                return self._build_index(params)
            elif operation == "load_index":
                return self._load_index(params)
            else:
                return self._error(f"Unknown operation: {operation}")
        except pymysql.Error as e:
            return self._error(f"Database error: {e}")
        except Exception as e:
            return self._error(f"Unexpected error: {e}")

    def get_runtime_snapshot(self) -> Dict[str, Any]:
        """Get runtime state for PreconditionEvaluator.

        Returns dict with: collections, indexed_collections,
        loaded_collections, connected.
        """
        snapshot = {
            "collections": [],
            "indexed_collections": [],
            "loaded_collections": [],
            "connected": False
        }

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get all tables (collections)
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            snapshot["collections"] = [t[list(t.keys())[0]] for t in tables]

            # For S1, assume all tables are indexed and loaded
            # In S2, we can query actual index status
            snapshot["indexed_collections"] = snapshot["collections"].copy()
            snapshot["loaded_collections"] = snapshot["collections"].copy()
            snapshot["connected"] = True

            cursor.close()
        except Exception as e:
            snapshot["connected"] = False

        return snapshot

    def health_check(self) -> bool:
        """Check if seekdb is accessible."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except Exception:
            return False

    # Private operation methods with SQL mapping

    def _search(self, params: Dict) -> Dict[str, Any]:
        """Execute vector search operation.

        Parameter mapping:
        - collection_name → table name
        - vector → query vector for l2_distance()
        - top_k → LIMIT

        SQL: SELECT id, l2_distance(embedding, '[...]') AS distance
             FROM table ORDER BY distance LIMIT k
        """
        collection_name = params.get("collection_name", self.collection)
        vector = params.get("vector", [])
        top_k = params.get("top_k", 10)

        if not vector:
            return self._error("Empty vector")

        # Convert vector to seekdb literal format '[x, y, z]'
        vector_literal = self._vector_to_literal(vector)

        conn = self._get_connection()
        cursor = conn.cursor()

        # Build SQL query - assumes embedding column exists
        sql = f"""
            SELECT id, l2_distance(embedding, %s) AS distance
            FROM {collection_name}
            ORDER BY distance
            LIMIT %s
        """

        cursor.execute(sql, (vector_literal, top_k))
        results = cursor.fetchall()
        cursor.close()

        # Normalize to standard format
        normalized = [
            {"id": r["id"], "score": float(r["distance"])}
            for r in results
        ]

        return {
            "status": "success",
            "operation": "search",
            "data": normalized
        }

    def _filtered_search(self, params: Dict) -> Dict[str, Any]:
        """Execute filtered search operation.

        Parameter mapping:
        - collection_name → table name
        - vector → query vector
        - top_k → LIMIT
        - filter → WHERE clause

        SQL: SELECT id, l2_distance(embedding, '[...]') AS distance
             FROM table WHERE filter ORDER BY distance LIMIT k
        """
        collection_name = params.get("collection_name", self.collection)
        vector = params.get("vector", [])
        top_k = params.get("top_k", 10)
        filter_expr = params.get("filter", "")

        if not vector:
            return self._error("Empty vector")

        vector_literal = self._vector_to_literal(vector)

        conn = self._get_connection()
        cursor = conn.cursor()

        # Build SQL with WHERE clause if filter provided
        where_clause = f"WHERE {filter_expr}" if filter_expr else ""
        sql = f"""
            SELECT id, l2_distance(embedding, %s) AS distance
            FROM {collection_name}
            {where_clause}
            ORDER BY distance
            LIMIT %s
        """

        cursor.execute(sql, (vector_literal, top_k))
        results = cursor.fetchall()
        cursor.close()

        normalized = [
            {"id": r["id"], "score": float(r["distance"])}
            for r in results
        ]

        return {
            "status": "success",
            "operation": "filtered_search",
            "data": normalized
        }

    def _hybrid_search(self, params: Dict) -> Dict[str, Any]:
        """Execute hybrid search (vector + text).

        For S1, hybrid search falls back to vector search.
        In S2, this can be extended with text search capabilities.

        Parameter mapping:
        - collection_name → table name
        - vector → query vector
        - top_k → LIMIT
        - query_text → (ignored in S1)
        """
        # S1: Hybrid search is just vector search
        return self._search(params)

    def _insert(self, params: Dict) -> Dict[str, Any]:
        """Insert documents with vectors.

        Parameter mapping:
        - collection_name → table name
        - vectors → list of vectors to insert

        SQL: INSERT INTO table (id, embedding) VALUES (1, '[...]'), (2, '[...]')
        """
        collection_name = params.get("collection_name", self.collection)
        vectors = params.get("vectors", [])

        if not vectors:
            return self._error("No vectors provided")

        conn = self._get_connection()
        cursor = conn.cursor()

        # Insert each vector with auto-incrementing id
        # Start from max(id) + 1 or 0 if table is empty
        cursor.execute(f"SELECT COALESCE(MAX(id), -1) + 1 AS next_id FROM {collection_name}")
        result = cursor.fetchone()
        next_id = result["next_id"] if result else 0

        inserted_ids = []
        for i, vec in enumerate(vectors):
            vec_literal = self._vector_to_literal(vec)
            cursor.execute(
                f"INSERT INTO {collection_name} (id, embedding) VALUES (%s, %s)",
                (next_id + i, vec_literal)
            )
            inserted_ids.append(next_id + i)

        conn.commit()
        cursor.close()

        return {
            "status": "success",
            "operation": "insert",
            "insert_count": len(vectors),
            "data": [{"id": id} for id in inserted_ids]
        }

    def _delete(self, params: Dict) -> Dict[str, Any]:
        """Delete documents by ID.

        Parameter mapping:
        - collection_name → table name
        - ids → list of IDs to delete

        SQL: DELETE FROM table WHERE id IN (...)
        """
        collection_name = params.get("collection_name", self.collection)
        ids = params.get("ids", [])

        if not ids:
            return self._error("No IDs provided")

        conn = self._get_connection()
        cursor = conn.cursor()

        placeholders = ",".join(["%s"] * len(ids))
        cursor.execute(
            f"DELETE FROM {collection_name} WHERE id IN ({placeholders})",
            ids
        )

        conn.commit()
        deleted_count = cursor.rowcount
        cursor.close()

        return {
            "status": "success",
            "operation": "delete",
            "data": {"deleted": deleted_count}
        }

    def _create_collection(self, params: Dict) -> Dict[str, Any]:
        """Create collection (table).

        Parameter mapping:
        - collection_name → table name
        - dimension → VECTOR(N) size
        - metric_type → (ignored in S1, seekdb uses L2 by default)

        SQL: CREATE TABLE table (id INT PRIMARY KEY, embedding VECTOR(N))
        """
        collection_name = params.get("collection_name")
        dimension = params.get("dimension", 128)
        metric_type = params.get("metric_type", "L2")

        if not collection_name:
            return self._error("collection_name required")

        conn = self._get_connection()
        cursor = conn.cursor()

        # Create table with vector column
        # Note: metric_type is ignored in S1 - seekdb defaults to L2
        cursor.execute(f"""
            CREATE TABLE {collection_name} (
                id INT PRIMARY KEY,
                embedding VECTOR({dimension})
            )
        """)

        conn.commit()
        cursor.close()

        return {
            "status": "success",
            "operation": "create_collection",
            "collection_name": collection_name,
            "data": [{"id": collection_name}]
        }

    def _drop_collection(self, params: Dict) -> Dict[str, Any]:
        """Drop collection (table).

        Parameter mapping:
        - collection_name → table name

        SQL: DROP TABLE table
        """
        collection_name = params.get("collection_name")

        if not collection_name:
            return self._error("collection_name required")

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(f"DROP TABLE IF EXISTS {collection_name}")
        conn.commit()
        cursor.close()

        return {
            "status": "success",
            "operation": "drop_collection",
            "data": []
        }

    def _build_index(self, params: Dict) -> Dict[str, Any]:
        """Build index.

        For S1, this is a no-op since seekdb handles indexing automatically.
        In S2, this can call explicit index building if needed.

        Parameter mapping:
        - collection_name → table name
        - index_type → (ignored in S1)
        """
        collection_name = params.get("collection_name", self.collection)

        # S1: No-op - seekdb handles indexing automatically
        return {
            "status": "success",
            "operation": "build_index",
            "collection_name": collection_name,
            "data": []
        }

    def _load_index(self, params: Dict) -> Dict[str, Any]:
        """Load index.

        For S1, this is a no-op since seekdb handles index loading automatically.
        In S2, this can call explicit index loading if needed.

        Parameter mapping:
        - collection_name → table name
        """
        collection_name = params.get("collection_name", self.collection)

        # S1: No-op - seekdb handles index loading automatically
        return {
            "status": "success",
            "operation": "load_index",
            "collection_name": collection_name,
            "data": []
        }

    # Helper methods

    def _vector_to_literal(self, vector: List[float]) -> str:
        """Convert vector list to seekdb vector literal.

        Example: [0.1, 0.2, 0.3] -> '[0.1, 0.2, 0.3]'
        """
        return "[" + ", ".join(str(v) for v in vector) + "]"

    def _error(self, message: str) -> Dict[str, Any]:
        """Build error response."""
        return {
            "status": "error",
            "error": message,
            "operation": "unknown"
        }
