"""Qdrant adapter for R4 differential testing.

Minimal implementation for pilot differential campaign.
Aligns with operation mapping in docs/R4_CAMPAIGN_PROPOSAL.md.
"""

from __future__ import annotations

from typing import Any, Dict, List

try:
    from qdrant_client import QdrantClient, models
except ImportError:
    raise ImportError(
        "qdrant-client not installed. Install with: pip install qdrant-client"
    )

from adapters.base import AdapterBase


class QdrantAdapter(AdapterBase):
    """Minimal Qdrant adapter for R4 differential testing.

    Implements 7 operations aligned with R4_CAMPAIGN_PROPOSAL.md:
    - create_collection: Direct mapping to client.create_collection()
    - insert: Maps to client.upsert() with PointStruct
    - search: Maps to client.search()
    - delete: Maps to client.delete() with PointIdsList
    - drop_collection: Direct mapping to client.delete_collection()
    - build_index: NO-OP (Qdrant auto-creates HNSW index)
    - load: NO-OP (Qdrant auto-loads collections)

    Key differences from Milvus:
    - Qdrant requires explicit IDs in PointStruct
    - Qdrant auto-creates indexes (no explicit build_index needed)
    - Qdrant auto-loads collections (no explicit load needed)
    """

    def __init__(self, connection_config: Dict[str, Any]):
        """Initialize Qdrant adapter with connection configuration.

        Args:
            connection_config: Dict with keys:
                - url (str): Qdrant URL, default "http://localhost:6333"
                - timeout (float): Request timeout in seconds, default 30.0
        """
        self.url = connection_config.get("url", "http://localhost:6333")
        self.timeout = connection_config.get("timeout", 30.0)
        self._client = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Qdrant."""
        self._client = QdrantClient(url=self.url, timeout=self.timeout)

    @property
    def client(self) -> QdrantClient:
        """Get Qdrant client, connecting if needed."""
        if self._client is None:
            self._connect()
        return self._client

    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Qdrant operation.

        Args:
            request: Dict with keys:
                - operation (str): Operation name
                - params (dict): Operation parameters

        Returns:
            Response dict with:
                - status (str): "success" or "error"
                - data (dict): Operation-specific data (on success)
                - error (str): Error message (on error)
                - error_type (str): Exception type name (on error)
        """
        operation = request.get("operation")
        params = request.get("params", {})

        try:
            if operation == "create_collection":
                return self._create_collection(params)
            elif operation == "insert":
                return self._insert(params)
            elif operation == "search":
                return self._search(params)
            elif operation == "delete":
                return self._delete(params)
            elif operation == "drop_collection":
                return self._drop_collection(params)
            elif operation == "build_index":
                return self._build_index(params)
            elif operation == "load":
                return self._load(params)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown operation: {operation}",
                    "error_type": "ValueError"
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _create_collection(self, params: Dict) -> Dict[str, Any]:
        """Create a new Qdrant collection.

        Args:
            params: Dict with keys:
                - collection_name (str): Name of collection
                - dimension (int): Vector dimension
                - metric_type (str): Distance metric ("COSINE", "L2", "IP")

        Returns:
            Success response with creation confirmation
        """
        collection_name = params["collection_name"]
        dimension = params["dimension"]
        metric_type = params.get("metric_type", "COSINE")

        # Map metric type to Qdrant Distance enum
        metric_map = {
            "COSINE": models.Distance.COSINE,
            "L2": models.Distance.EUCLID,
            "IP": models.Distance.DOT,
        }
        distance = metric_map.get(metric_type, models.Distance.COSINE)

        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=dimension, distance=distance)
        )

        return {
            "status": "success",
            "data": {
                "collection_name": collection_name,
                "dimension": dimension,
                "metric_type": metric_type
            }
        }

    def _insert(self, params: Dict) -> Dict[str, Any]:
        """Insert/upsert vectors into collection.

        Qdrant requires explicit IDs. If not provided, auto-generates sequential IDs.

        Args:
            params: Dict with keys:
                - collection_name (str): Name of collection
                - vectors (list): List of vector arrays
                - ids (list, optional): List of IDs (auto-generated if not provided)
                - payload (dict, optional): Payload data for vectors

        Returns:
            Success response with count of inserted points
        """
        collection_name = params["collection_name"]
        vectors = params["vectors"]
        ids = params.get("ids")
        payload = params.get("payload", {})

        # Auto-generate IDs if not provided
        if ids is None:
            ids = list(range(len(vectors)))

        # Create PointStruct objects
        points = [
            models.PointStruct(
                id=ids[i],
                vector=vectors[i],
                payload=payload if isinstance(payload, dict) else payload.get(i, {})
            )
            for i in range(len(vectors))
        ]

        # Upsert points
        operation_info = self.client.upsert(
            collection_name=collection_name,
            points=points
        )

        return {
            "status": "success",
            "data": {
                "collection_name": collection_name,
                "inserted_count": len(points),
                "ids": ids
            }
        }

    def _search(self, params: Dict) -> Dict[str, Any]:
        """Search for similar vectors.

        Args:
            params: Dict with keys:
                - collection_name (str): Name of collection
                - query_vector (list): Query vector
                - top_k (int): Number of results to return

        Returns:
            Success response with search results
        """
        collection_name = params["collection_name"]
        query_vector = params["query_vector"]
        top_k = params.get("top_k", 10)

        # Search
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k
        )

        # Normalize results to common format
        normalized_results = [
            {
                "id": r.id,
                "score": r.score,
                "payload": r.payload if hasattr(r, 'payload') else {}
            }
            for r in results
        ]

        return {
            "status": "success",
            "data": {
                "collection_name": collection_name,
                "results": normalized_results,
                "count": len(normalized_results)
            }
        }

    def _delete(self, params: Dict) -> Dict[str, Any]:
        """Delete points by IDs.

        Args:
            params: Dict with keys:
                - collection_name (str): Name of collection
                - ids (list): List of point IDs to delete

        Returns:
            Success response with deletion confirmation
        """
        collection_name = params["collection_name"]
        ids = params["ids"]

        # Delete by IDs
        self.client.delete(
            collection_name=collection_name,
            points_selector=models.PointIdsList(points=ids)
        )

        return {
            "status": "success",
            "data": {
                "collection_name": collection_name,
                "deleted_ids": ids,
                "deleted_count": len(ids)
            }
        }

    def _drop_collection(self, params: Dict) -> Dict[str, Any]:
        """Delete a collection.

        Args:
            params: Dict with keys:
                - collection_name (str): Name of collection to delete

        Returns:
            Success response with deletion confirmation
        """
        collection_name = params["collection_name"]

        self.client.delete_collection(collection_name=collection_name)

        return {
            "status": "success",
            "data": {
                "collection_name": collection_name,
                "deleted": True
            }
        }

    def _build_index(self, params: Dict) -> Dict[str, Any]:
        """NO-OP: Qdrant auto-creates HNSW index.

        This method exists for compatibility with the Milvus adapter interface.
        Qdrant automatically creates HNSW indexes when vectors are upserted.

        Args:
            params: Ignored (kept for interface compatibility)

        Returns:
            Success response noting auto-index behavior
        """
        return {
            "status": "success",
            "data": {
                "note": "Qdrant auto-creates HNSW index",
                "operation": "no-op"
            }
        }

    def _load(self, params: Dict) -> Dict[str, Any]:
        """NO-OP: Qdrant auto-loads collections.

        This method exists for compatibility with the Milvus adapter interface.
        Qdrant automatically loads collections into memory when accessed.

        Args:
            params: Ignored (kept for interface compatibility)

        Returns:
            Success response noting auto-load behavior
        """
        return {
            "status": "success",
            "data": {
                "note": "Qdrant auto-loads collections",
                "operation": "no-op"
            }
        }

    def health_check(self) -> bool:
        """Check if Qdrant connection is healthy.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            # Try to get collections list
            self.client.get_collections()
            return True
        except Exception:
            return False
