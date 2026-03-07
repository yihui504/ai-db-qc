"""Minimal seekdb adapter for AI-native database testing.

This adapter provides a thin parameter mapping layer to reuse existing
test case families with seekdb's AI-native search capabilities.
"""

from __future__ import annotations

import requests
from typing import Any, Dict, List

from adapters.base import AdapterBase


class SeekDBAdapter(AdapterBase):
    """Minimal adapter for seekdb AI-native search database.

    Focus: Get basic operations working with minimal complexity.
    Reuses: existing triage, oracles, evidence pipeline.

    Architecture:
    - Maps generic operations to seekdb REST API
    - Thin parameter mapping layer for Milvus-shaped parameters
    - Handles hybrid, vector, and keyword search transparently
    """

    def __init__(
        self,
        api_endpoint: str,
        api_key: str,
        collection: str = "default",
        timeout: int = 30
    ):
        """Initialize seekdb adapter.

        Args:
            api_endpoint: seekdb API endpoint (e.g., "https://api.seekdb.ai")
            api_key: seekdb API key for authentication
            collection: Default collection name
            timeout: Request timeout in seconds
        """
        self.api_endpoint = api_endpoint.rstrip("/")
        self.api_key = api_key
        self.collection = collection
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute request against seekdb.

        Maps generic operations to seekdb API calls with parameter mapping.

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
        except requests.RequestException as e:
            return self._error(f"Network error: {e}")
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
            response = self.session.get(
                f"{self.api_endpoint}/collections",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                snapshot["collections"] = data.get("collections", [])
                snapshot["indexed_collections"] = [
                    c for c in snapshot["collections"]
                    if data.get("indexes", {}).get(c, False)
                ]
                snapshot["loaded_collections"] = [
                    c for c in snapshot["collections"]
                    if data.get("loaded", {}).get(c, False)
                ]
                snapshot["connected"] = True
        except Exception:
            snapshot["connected"] = False

        return snapshot

    def health_check(self) -> bool:
        """Check if seekdb is accessible."""
        try:
            response = self.session.get(
                f"{self.api_endpoint}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False

    # Private operation methods with parameter mapping

    def _search(self, params: Dict) -> Dict[str, Any]:
        """Execute vector search operation.

        Parameter mapping:
        - collection_name → collection
        - vector → vector
        - top_k → limit
        """
        collection_name = params.get("collection_name", self.collection)
        vector = params.get("vector", [])
        top_k = params.get("top_k", 10)

        payload = {
            "collection": collection_name,
            "vector": vector,
            "limit": top_k
        }

        response = self.session.post(
            f"{self.api_endpoint}/search/vector",
            json=payload,
            timeout=self.timeout
        )

        if response.status_code == 200:
            data = response.json()
            # Normalize to standard format
            results = [
                {"id": r.get("id"), "score": r.get("score", 0.0)}
                for r in data.get("results", [])
            ]
            return {
                "status": "success",
                "operation": "search",
                "data": results
            }
        else:
            return self._error_from_response(response)

    def _filtered_search(self, params: Dict) -> Dict[str, Any]:
        """Execute filtered search operation.

        Parameter mapping:
        - collection_name → collection
        - vector → vector
        - top_k → limit
        - filter → filter_expression
        """
        collection_name = params.get("collection_name", self.collection)
        vector = params.get("vector", [])
        top_k = params.get("top_k", 10)
        filter_expr = params.get("filter", "")

        payload = {
            "collection": collection_name,
            "vector": vector,
            "limit": top_k,
            "filter_expression": filter_expr
        }

        response = self.session.post(
            f"{self.api_endpoint}/search/filtered",
            json=payload,
            timeout=self.timeout
        )

        if response.status_code == 200:
            data = response.json()
            results = [
                {"id": r.get("id"), "score": r.get("score", 0.0)}
                for r in data.get("results", [])
            ]
            return {
                "status": "success",
                "operation": "filtered_search",
                "data": results
            }
        else:
            return self._error_from_response(response)

    def _hybrid_search(self, params: Dict) -> Dict[str, Any]:
        """Execute hybrid search (vector + keyword).

        Parameter mapping:
        - collection_name → collection
        - vector → vector
        - top_k → limit
        - query_text (optional) → query_text
        """
        collection_name = params.get("collection_name", self.collection)
        vector = params.get("vector", [])
        top_k = params.get("top_k", 10)
        query_text = params.get("query_text", "")

        payload = {
            "collection": collection_name,
            "vector": vector,
            "query": query_text,
            "limit": top_k
        }

        response = self.session.post(
            f"{self.api_endpoint}/search/hybrid",
            json=payload,
            timeout=self.timeout
        )

        if response.status_code == 200:
            data = response.json()
            results = [
                {"id": r.get("id"), "score": r.get("score", 0.0)}
                for r in data.get("results", [])
            ]
            return {
                "status": "success",
                "operation": "hybrid_search",
                "data": results
            }
        else:
            return self._error_from_response(response)

    def _insert(self, params: Dict) -> Dict[str, Any]:
        """Insert documents.

        Parameter mapping:
        - collection_name → collection
        - vectors → documents (with vector field)
        """
        collection_name = params.get("collection_name", self.collection)
        vectors = params.get("vectors", [])

        # Map vectors to documents
        documents = [
            {"id": i, "vector": vec}
            for i, vec in enumerate(vectors)
        ]

        payload = {
            "collection": collection_name,
            "documents": documents
        }

        response = self.session.post(
            f"{self.api_endpoint}/documents",
            json=payload,
            timeout=self.timeout
        )

        if response.status_code in [200, 201]:
            data = response.json()
            return {
                "status": "success",
                "operation": "insert",
                "insert_count": data.get("inserted_count", len(documents)),
                "data": documents
            }
        else:
            return self._error_from_response(response)

    def _delete(self, params: Dict) -> Dict[str, Any]:
        """Delete documents.

        Parameter mapping:
        - collection_name → collection
        - ids → ids
        """
        collection_name = params.get("collection_name", self.collection)
        ids = params.get("ids", [])

        payload = {
            "collection": collection_name,
            "ids": ids
        }

        response = self.session.delete(
            f"{self.api_endpoint}/documents",
            json=payload,
            timeout=self.timeout
        )

        if response.status_code == 200:
            return {
                "status": "success",
                "operation": "delete",
                "data": {"deleted": len(ids)}
            }
        else:
            return self._error_from_response(response)

    def _create_collection(self, params: Dict) -> Dict[str, Any]:
        """Create collection.

        Parameter mapping:
        - collection_name → name
        - dimension → dimension
        - metric_type → metric_type
        """
        collection_name = params.get("collection_name")
        dimension = params.get("dimension", 1536)
        metric_type = params.get("metric_type", "L2")

        payload = {
            "name": collection_name,
            "dimension": dimension,
            "metric_type": metric_type
        }

        response = self.session.put(
            f"{self.api_endpoint}/collections",
            json=payload,
            timeout=self.timeout
        )

        if response.status_code in [200, 201]:
            return {
                "status": "success",
                "operation": "create_collection",
                "collection_name": collection_name,
                "data": [{"id": collection_name}]
            }
        else:
            return self._error_from_response(response)

    def _drop_collection(self, params: Dict) -> Dict[str, Any]:
        """Drop collection.

        Parameter mapping:
        - collection_name → name
        """
        collection_name = params.get("collection_name")

        response = self.session.delete(
            f"{self.api_endpoint}/collections/{collection_name}",
            timeout=self.timeout
        )

        if response.status_code == 200:
            return {
                "status": "success",
                "operation": "drop_collection",
                "data": []
            }
        else:
            return self._error_from_response(response)

    def _build_index(self, params: Dict) -> Dict[str, Any]:
        """Build index.

        Parameter mapping:
        - collection_name → collection
        - index_type → index_type
        """
        collection_name = params.get("collection_name", self.collection)
        index_type = params.get("index_type", "IVF_FLAT")

        payload = {
            "collection": collection_name,
            "index_type": index_type
        }

        response = self.session.post(
            f"{self.api_endpoint}/indexes",
            json=payload,
            timeout=self.timeout
        )

        if response.status_code in [200, 201]:
            return {
                "status": "success",
                "operation": "build_index",
                "collection_name": collection_name,
                "data": []
            }
        else:
            return self._error_from_response(response)

    def _load_index(self, params: Dict) -> Dict[str, Any]:
        """Load index.

        Parameter mapping:
        - collection_name → collection
        """
        collection_name = params.get("collection_name", self.collection)

        payload = {
            "collection": collection_name
        }

        response = self.session.post(
            f"{self.api_endpoint}/indexes/load",
            json=payload,
            timeout=self.timeout
        )

        if response.status_code == 200:
            return {
                "status": "success",
                "operation": "load_index",
                "collection_name": collection_name,
                "data": []
            }
        else:
            return self._error_from_response(response)

    # Error handling helpers

    def _error(self, message: str) -> Dict[str, Any]:
        """Build error response."""
        return {
            "status": "error",
            "error": message,
            "operation": "unknown"
        }

    def _error_from_response(self, response) -> Dict[str, Any]:
        """Build error response from HTTP response.

        Extracts error message for triage classification.
        """
        try:
            error_data = response.json()
            error_msg = error_data.get(
                "message",
                error_data.get("error", f"HTTP {response.status_code}")
            )
        except Exception:
            error_msg = f"HTTP {response.status_code}: {response.text[:200]}"

        return {
            "status": "error",
            "error": error_msg,
            "operation": "unknown",
            "status_code": response.status_code
        }
