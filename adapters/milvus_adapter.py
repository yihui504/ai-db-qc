"""Milvus adapter for real database validation."""

from __future__ import annotations

from typing import Any, Dict, List

from adapters.base import AdapterBase
from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility


class MilvusAdapter(AdapterBase):
    """Minimal Milvus adapter for real database validation.

    Implements 8 operations: create_collection, insert, build_index, load,
    search, filtered_search, health_check, get_runtime_snapshot.
    """

    def __init__(self, connection_config: Dict[str, Any]):
        """Initialize Milvus adapter with connection configuration.

        Args:
            connection_config: Dict with keys:
                - host (str): Milvus host, default "localhost"
                - port (int): Milvus port, default 19530
                - alias (str): Connection alias, default "default"
        """
        self.host = connection_config.get("host", "localhost")
        self.port = connection_config.get("port", 19530)
        self.alias = connection_config.get("alias", "default")
        self.timeout = connection_config.get("timeout", 10)
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Milvus."""
        connections.connect(
            alias=self.alias,
            host=self.host,
            port=self.port
        )

    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Milvus operation.

        Args:
            request: Dict with keys:
                - operation (str): Operation name
                - params (dict): Operation parameters

        Returns:
            Response dict with status, data, or error
        """
        operation = request.get("operation")
        params = request.get("params", {})

        try:
            if operation == "create_collection":
                return self._create_collection(params)
            elif operation == "insert":
                return self._insert(params)
            elif operation == "build_index":
                return self._build_index(params)
            elif operation == "load":
                return self._load(params)
            elif operation == "search":
                return self._search(params)
            elif operation == "filtered_search":
                return self._filtered_search(params)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown operation: {operation}"
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "operation": operation
            }

    def get_runtime_snapshot(self) -> Dict[str, Any]:
        """Get runtime state for PreconditionEvaluator.

        Returns simple dict with: collections, indexed_collections,
        loaded_collections, connected, memory_stats.
        """
        snapshot = {
            "collections": [],
            "indexed_collections": [],
            "loaded_collections": [],
            "connected": True,
            "memory_stats": {}
        }

        try:
            snapshot["collections"] = utility.list_collections(using=self.alias)

            for col_name in snapshot["collections"]:
                try:
                    col = Collection(col_name, using=self.alias)
                    # Check for indexes - robust to different pymilvus versions
                    if hasattr(col, 'indexes') and col.indexes:
                        snapshot["indexed_collections"].append(col_name)
                    # Check if loaded - robust to different pymilvus versions
                    if hasattr(col, 'loaded') and col.loaded:
                        snapshot["loaded_collections"].append(col_name)
                except Exception:
                    # Skip individual collection errors, continue with others
                    continue

        except Exception:
            snapshot["connected"] = False

        return snapshot

    def health_check(self) -> bool:
        """Check if Milvus is responsive."""
        try:
            version = utility.get_server_version(using=self.alias)
            return version is not None
        except Exception:
            return False

    def close(self) -> None:
        """Close connection."""
        try:
            connections.disconnect(self.alias)
        except Exception:
            pass

    # Private operation methods

    def _create_collection(self, params: Dict) -> Dict[str, Any]:
        """Create a new collection."""
        collection_name = params.get("collection_name")
        dimension = params.get("dimension", 128)
        metric_type = params.get("metric_type", "L2")

        # Define schema with proper DataType enums
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension)
        ]
        schema = CollectionSchema(fields, f"Auto generated schema for {collection_name}")

        # Create collection
        collection = Collection(name=collection_name, schema=schema, using=self.alias)

        return {
            "status": "success",
            "operation": "create_collection",
            "collection_name": collection_name,
            "data": [{"id": collection_name}]
        }

    def _insert(self, params: Dict) -> Dict[str, Any]:
        """Insert vectors into collection."""
        collection_name = params.get("collection_name")
        vectors = params.get("vectors", [])

        collection = Collection(collection_name, using=self.alias)

        # Prepare data
        data = []
        for i, vec in enumerate(vectors):
            data.append({"id": i, "vector": vec})

        result = collection.insert(data)

        return {
            "status": "success",
            "operation": "insert",
            "collection_name": collection_name,
            "insert_count": result.insert_count,
            "data": [{"id": i, "vector": vec} for i, vec in enumerate(vectors)]
        }

    def _build_index(self, params: Dict) -> Dict[str, Any]:
        """Build index on collection."""
        collection_name = params.get("collection_name")
        index_type = params.get("index_type", "IVF_FLAT")
        metric_type = params.get("metric_type", "L2")

        collection = Collection(collection_name, using=self.alias)

        # Create index on vector field
        index_params = {
            "index_type": index_type,
            "metric_type": metric_type,
            "params": {"nlist": 128}
        }

        collection.create_index(
            field_name="vector",
            index_params=index_params
        )

        return {
            "status": "success",
            "operation": "build_index",
            "collection_name": collection_name,
            "data": []
        }

    def _load(self, params: Dict) -> Dict[str, Any]:
        """Load collection into memory."""
        collection_name = params.get("collection_name")

        collection = Collection(collection_name, using=self.alias)
        collection.load()

        return {
            "status": "success",
            "operation": "load",
            "collection_name": collection_name,
            "data": []
        }

    def _search(self, params: Dict) -> Dict[str, Any]:
        """Search for similar vectors."""
        collection_name = params.get("collection_name")
        vector = params.get("vector", [])
        top_k = params.get("top_k", 10)

        collection = Collection(collection_name, using=self.alias)

        # Search parameters
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

        results = collection.search(
            data=[vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=None
        )

        # Format results
        formatted_results = []
        for hit in results[0]:
            formatted_results.append({
                "id": hit.id,
                "score": hit.score,
                "distance": hit.distance
            })

        return {
            "status": "success",
            "operation": "search",
            "collection_name": collection_name,
            "data": formatted_results
        }

    def _filtered_search(self, params: Dict) -> Dict[str, Any]:
        """Search with filter expression."""
        collection_name = params.get("collection_name")
        vector = params.get("vector", [])
        top_k = params.get("top_k", 10)
        filter_expr = params.get("filter", "")

        collection = Collection(collection_name, using=self.alias)

        # Search parameters
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

        results = collection.search(
            data=[vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=filter_expr
        )

        # Format results
        formatted_results = []
        for hit in results[0]:
            formatted_results.append({
                "id": hit.id,
                "score": hit.score,
                "distance": hit.distance
            })

        return {
            "status": "success",
            "operation": "filtered_search",
            "collection_name": collection_name,
            "data": formatted_results
        }
