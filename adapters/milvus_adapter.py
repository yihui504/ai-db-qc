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

    def supported_operations(self) -> List[str]:
        """Return list of operations supported by MilvusAdapter."""
        return [
            "create_collection", "insert", "insert_unique", "search", "search_exact",
            "wait", "build_index", "load", "filtered_search", "drop_collection",
            "delete", "release", "reload", "drop_index", "flush", "get_load_state",
            "count_entities", "describe_collection"
        ]

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
            elif operation == "insert_unique":
                return self._insert(params)  # Same operation, different semantic use
            elif operation == "search":
                return self._search(params)
            elif operation == "search_exact":
                return self._search(params)  # Same operation, exact vector query
            elif operation == "wait":
                return self._wait(params)
            elif operation == "build_index":
                return self._build_index(params)
            elif operation == "load":
                return self._load(params)
            elif operation == "filtered_search":
                return self._filtered_search(params)
            elif operation == "drop_collection":
                return self._drop_collection(params)
            elif operation == "delete":
                return self._delete(params)
            elif operation == "release":
                return self._release(params)
            elif operation == "reload":
                return self._reload(params)
            elif operation == "drop_index":
                return self._drop_index(params)
            elif operation == "flush":
                return self._flush(params)
            elif operation == "get_load_state":
                return self._get_load_state(params)
            elif operation == "count_entities":
                return self._count_entities(params)
            elif operation == "describe_collection":
                return self._describe_collection(params)
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

    def _parse_vectors(self, vectors: Any) -> list:
        """Parse vectors from string or list format.

        Handles cases where vectors are passed as strings (from template substitution)
        or as actual Python lists.

        Args:
            vectors: Either a list of lists, a string representation like "[[0.1, 0.2], ...]",
                     or a flat list like "[0.1, 0.2, ...]"

        Returns:
            List of vector lists (always nested)
        """
        import ast

        if isinstance(vectors, str):
            try:
                # Parse string representation of list
                parsed = ast.literal_eval(vectors)
                if isinstance(parsed, list):
                    # Check if it's a flat list or nested list
                    if parsed and isinstance(parsed[0], (int, float)):
                        # Flat list - wrap in another list
                        return [parsed]
                    elif parsed and isinstance(parsed[0], list):
                        # Already nested list
                        return parsed
                    else:
                        # Empty list
                        return []
                return [parsed]
            except (ValueError, SyntaxError):
                # If parsing fails, return as single-item list
                return [[vectors]]
        elif isinstance(vectors, list):
            # Already a list, ensure it's nested
            if vectors and isinstance(vectors[0], (int, float)):
                return [vectors]
            return vectors
        else:
            return [[vectors]]

    # Private operation methods

    def _create_collection(self, params: Dict) -> Dict[str, Any]:
        """Create a new collection with optional scalar fields."""
        collection_name = params.get("collection_name")
        dimension = params.get("dimension", 128)
        metric_type = params.get("metric_type", "L2")
        scalar_fields = params.get("scalar_fields", [])
        enable_dynamic_field = params.get("enable_dynamic_field", False)

        # Define schema with proper DataType enums
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension)
        ]

        # Add scalar fields if specified
        for field_name in scalar_fields:
            # For simplicity, treat all scalar fields as VARCHAR (string)
            # In production, you'd want to infer types from the data
            fields.append(
                FieldSchema(name=field_name, dtype=DataType.VARCHAR, max_length=256)
            )

        schema = CollectionSchema(
            fields,
            f"Auto generated schema for {collection_name}",
            enable_dynamic_field=enable_dynamic_field,
        )

        # Create collection
        collection = Collection(name=collection_name, schema=schema, using=self.alias)

        return {
            "status": "success",
            "operation": "create_collection",
            "collection_name": collection_name,
            "data": [{"id": collection_name}]
        }

    def _insert(self, params: Dict) -> Dict[str, Any]:
        """Insert vectors with optional scalar data into collection."""
        collection_name = params.get("collection_name")
        vectors = params.get("vectors", [])
        scalar_data = params.get("scalar_data", [])
        ids = params.get("ids", [])  # Support explicit IDs parameter

        # Parse vector strings if needed (instantiator substitutes strings)
        vectors = self._parse_vectors(vectors)

        collection = Collection(collection_name, using=self.alias)

        # Prepare data - need to handle scalar fields
        if scalar_data:
            # Merge scalar data with vectors
            # scalar_data format: [{'id': 1, 'color': 'red', 'status': 'active'}, ...]
            data = []
            for i, vec in enumerate(vectors):
                entity = {"id": scalar_data[i].get("id", i), "vector": vec}
                # Add scalar fields
                for key, value in scalar_data[i].items():
                    if key != "id":
                        entity[key] = value
                data.append(entity)
        elif ids:
            # Explicit IDs provided - convert string IDs to integers
            converted_ids = self._convert_ids_to_int(ids)
            data = []
            for i, vec in enumerate(vectors):
                data.append({"id": converted_ids[i] if i < len(converted_ids) else i, "vector": vec})
        else:
            # No scalar data - just vectors
            data = []
            for i, vec in enumerate(vectors):
                data.append({"id": i, "vector": vec})

        result = collection.insert(data)

        return {
            "status": "success",
            "operation": "insert",
            "collection_name": collection_name,
            "insert_count": result.insert_count,
            "data": data
        }

    def _build_index(self, params: Dict) -> Dict[str, Any]:
        """Build index on collection with fully configurable parameters.

        Supports IVF_FLAT, IVF_SQ8, HNSW, FLAT index types.
        All algorithm parameters are now exposed (no more hardcoded values).
        """
        collection_name = params.get("collection_name")
        index_type = params.get("index_type", "IVF_FLAT")
        metric_type = params.get("metric_type", "L2")

        collection = Collection(collection_name, using=self.alias)

        # Build algorithm-specific params (fully configurable, no hardcoded values)
        algo_params: Dict[str, Any] = {}
        if index_type in ("IVF_FLAT", "IVF_SQ8", "IVF_PQ"):
            algo_params["nlist"] = int(params.get("nlist", 128))
        elif index_type == "HNSW":
            algo_params["M"] = int(params.get("M", 16))
            algo_params["efConstruction"] = int(params.get("efConstruction", 200))
        elif index_type == "FLAT":
            pass  # FLAT has no algorithm parameters
        elif index_type == "DISKANN":
            algo_params["search_list"] = int(params.get("search_list", 100))
        else:
            # Unknown index type: pass any extra params through
            for k, v in params.items():
                if k not in ("collection_name", "index_type", "metric_type", "field_name"):
                    algo_params[k] = v

        index_params = {
            "index_type": index_type,
            "metric_type": metric_type,
            "params": algo_params,
        }

        field_name = params.get("field_name", "vector")
        collection.create_index(field_name=field_name, index_params=index_params)

        return {
            "status": "success",
            "operation": "build_index",
            "collection_name": collection_name,
            "index_type": index_type,
            "metric_type": metric_type,
            "algo_params": algo_params,
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
        """Search for similar vectors, returning scalar fields if present."""
        collection_name = params.get("collection_name")
        vector = params.get("vector", [])
        top_k = params.get("top_k", 10)

        # Parse vector string if needed
        if isinstance(vector, str):
            vector = self._parse_vectors(vector)[0]

        collection = Collection(collection_name, using=self.alias)

        # Get output fields to return (all fields if collection has scalars)
        output_fields = ["id", "vector"]
        try:
            schema = collection.schema
            for field in schema.fields:
                if field.name not in ["id", "vector"]:
                    output_fields.append(field.name)
        except Exception:
            pass  # Use default fields

        # Search parameters
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

        results = collection.search(
            data=[vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=None,
            output_fields=output_fields
        )

        # Format results with scalar fields
        formatted_results = []
        for hit in results[0]:
            result_entry = {
                "id": hit.id,
                "score": hit.score,
                "distance": hit.distance,
                "scalar_fields": {}
            }
            # Add scalar fields if present
            for field in output_fields:
                if field not in ["id", "vector"] and hasattr(hit, field):
                    result_entry["scalar_fields"][field] = getattr(hit, field)
                elif field not in ["id", "vector"] and hasattr(hit, 'entity'):
                    result_entry["scalar_fields"][field] = hit.entity.get(field)

            formatted_results.append(result_entry)

        return {
            "status": "success",
            "operation": "search",
            "collection_name": collection_name,
            "data": formatted_results
        }

    def _filtered_search(self, params: Dict) -> Dict[str, Any]:
        """Search with filter expression, returning scalar fields."""
        collection_name = params.get("collection_name")
        vector = params.get("vector", [])
        top_k = params.get("top_k", 10)
        filter_expr = params.get("filter", "")

        # Parse vector string if needed
        if isinstance(vector, str):
            vector = self._parse_vectors(vector)[0]

        collection = Collection(collection_name, using=self.alias)

        # Get output fields to return (all fields if collection has scalars)
        output_fields = ["id", "vector"]
        try:
            schema = collection.schema
            for field in schema.fields:
                if field.name not in ["id", "vector"]:
                    output_fields.append(field.name)
        except Exception:
            pass  # Use default fields

        # Search parameters
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

        # Convert filter dict to expression string if needed
        if isinstance(filter_expr, dict):
            expr_parts = []
            for key, value in filter_expr.items():
                if value is None:
                    expr_parts.append(f"{key} is null")
                elif isinstance(value, (list, set)):
                    # IN clause
                    value_str = ', '.join(f"'{v}'" for v in value)
                    expr_parts.append(f"{key} in [{value_str}]")
                else:
                    expr_parts.append(f"{key} == '{value}'")
            filter_expr = " and ".join(expr_parts) if expr_parts else ""

        results = collection.search(
            data=[vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=filter_expr if filter_expr else None,
            output_fields=output_fields
        )

        # Format results with scalar fields
        formatted_results = []
        for hit in results[0]:
            result_entry = {
                "id": hit.id,
                "score": hit.score,
                "distance": hit.distance,
                "scalar_fields": {}
            }
            # Add scalar fields if present
            for field in output_fields:
                if field not in ["id", "vector"] and hasattr(hit, field):
                    result_entry["scalar_fields"][field] = getattr(hit, field)
                elif field not in ["id", "vector"] and hasattr(hit, 'entity'):
                    result_entry["scalar_fields"][field] = hit.entity.get(field)

            formatted_results.append(result_entry)

        return {
            "status": "success",
            "operation": "filtered_search",
            "collection_name": collection_name,
            "data": formatted_results
        }

    def _drop_collection(self, params: Dict) -> Dict[str, Any]:
        """Drop a collection."""
        collection_name = params.get("collection_name")

        try:
            utility.drop_collection(collection_name, using=self.alias)
            return {
                "status": "success",
                "operation": "drop_collection",
                "data": []
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "operation": "drop_collection"
            }

    def _delete(self, params: Dict) -> Dict[str, Any]:
        """Delete entities by ID.

        Args:
            params: Dict with keys:
                - collection_name (str): Collection name
                - ids (list): List of IDs to delete

        Returns:
            Response dict with status and delete_count
        """
        collection_name = params.get("collection_name")
        ids = params.get("ids", [])

        if not ids:
            return {
                "status": "error",
                "error": "No IDs provided for deletion",
                "operation": "delete"
            }

        try:
            collection = Collection(collection_name, using=self.alias)
            # Convert string IDs to integers for Milvus compatibility
            converted_ids = self._convert_ids_to_int(ids)
            result = collection.delete(expr=f"id in {converted_ids}")
            return {
                "status": "success",
                "operation": "delete",
                "collection_name": collection_name,
                "delete_count": result.delete_count,
                "data": []
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "operation": "delete"
            }

    def _convert_ids_to_int(self, ids: List[Any]) -> List[int]:
        """Convert string IDs to integers for Milvus compatibility.
        
        Milvus requires INT64 IDs, but tests may pass string IDs like 'id_1'.
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

    def _release(self, params: Dict) -> Dict[str, Any]:
        """Release collection from memory (collection-level load state operation).

        Release unloads the searchable state while preserving index metadata.
        This is a collection-level operation, not an index-specific operation.

        Args:
            params: Dict with keys:
                - collection_name (str): Collection name

        Returns:
            Response dict with status and load state
        """
        collection_name = params.get("collection_name")

        try:
            collection = Collection(collection_name, using=self.alias)
            collection.release()

            # Verify load state after release (convert LoadState enum to string)
            from pymilvus.client.types import LoadState
            load_state_raw = utility.load_state(collection_name, using=self.alias)
            load_state_map = {
                LoadState.NotLoad: "NotLoad",
                LoadState.Loaded: "Loaded",
                LoadState.Loading: "Loading",
                LoadState.NotExist: "NotExist"
            }
            load_state = load_state_map.get(load_state_raw, str(load_state_raw))

            return {
                "status": "success",
                "operation": "release",
                "collection_name": collection_name,
                "load_state": load_state,
                "data": [{
                    "collection_name": collection_name,
                    "load_state": load_state,
                    "note": "release unloads searchable state, preserves index metadata"
                }]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "operation": "release"
            }

    def _reload(self, params: Dict) -> Dict[str, Any]:
        """Reload collection into memory after release.

        Args:
            params: Dict with keys:
                - collection_name (str): Collection name

        Returns:
            Response dict with status and load state
        """
        collection_name = params.get("collection_name")

        try:
            collection = Collection(collection_name, using=self.alias)
            collection.load()

            # Verify load state after reload (convert LoadState enum to string)
            from pymilvus.client.types import LoadState
            load_state_raw = utility.load_state(collection_name, using=self.alias)
            load_state_map = {
                LoadState.NotLoad: "NotLoad",
                LoadState.Loaded: "Loaded",
                LoadState.Loading: "Loading",
                LoadState.NotExist: "NotExist"
            }
            load_state = load_state_map.get(load_state_raw, str(load_state_raw))

            return {
                "status": "success",
                "operation": "reload",
                "collection_name": collection_name,
                "load_state": load_state,
                "entered_via": "reload_after_release",
                "data": [{
                    "collection_name": collection_name,
                    "load_state": load_state
                }]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "operation": "reload"
            }

    def _drop_index(self, params: Dict) -> Dict[str, Any]:
        """Drop index metadata from collection.

        This operation deletes index metadata. It is irreversible.

        Args:
            params: Dict with keys:
                - collection_name (str): Collection name

        Returns:
            Response dict with status
        """
        collection_name = params.get("collection_name")

        try:
            collection = Collection(collection_name, using=self.alias)

            # Get index info before dropping (for evidence)
            index_exists_before = False
            index_info_before = None
            try:
                if hasattr(collection, 'indexes') and collection.indexes:
                    index_exists_before = True
                    index_info_before = collection.indexes[0].to_dict()
            except Exception:
                pass

            # Drop the index
            collection.drop_index()

            # Verify index metadata after drop
            index_exists_after = False
            try:
                if hasattr(collection, 'indexes') and collection.indexes:
                    index_exists_after = True
            except Exception:
                pass

            return {
                "status": "success",
                "operation": "drop_index",
                "collection_name": collection_name,
                "index_exists_before": index_exists_before,
                "index_exists_after": index_exists_after,
                "index_info_before": index_info_before,
                "irreversible": True,
                "data": [{
                    "collection_name": collection_name,
                    "index_dropped": True
                }]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "operation": "drop_index"
            }

    def _get_load_state(self, params: Dict) -> Dict[str, Any]:
        """Query official load state using utility.load_state() API.

        Uses ONLY the official Milvus API. No fallback to undocumented attributes.
        If the API returns an error or uncertain state, the result is marked accordingly.

        Args:
            params: Dict with keys:
                - collection_name (str): Collection name

        Returns:
            Response dict with official load state
        """
        collection_name = params.get("collection_name")

        try:
            # Use official API only
            load_state_raw = utility.load_state(collection_name, using=self.alias)
            # Returns LoadState enum: NotLoad, Loaded, Loading, or NotExist
            # Convert enum to string for consistent serialization
            from pymilvus.client.types import LoadState

            # Map LoadState enum to string
            load_state_map = {
                LoadState.NotLoad: "NotLoad",
                LoadState.Loaded: "Loaded",
                LoadState.Loading: "Loading",
                LoadState.NotExist: "NotExist"
            }
            load_state = load_state_map.get(load_state_raw, str(load_state_raw))

            # If collection doesn't exist, handle explicitly
            if load_state == "NotExist":
                return {
                    "status": "success",
                    "operation": "get_load_state",
                    "collection_name": collection_name,
                    "load_state": "NotExist",
                    "index_metadata_exists": False,
                    "index_info": None,
                    "data": [{
                        "collection_name": collection_name,
                        "load_state": "NotExist",
                        "index_metadata_exists": False,
                        "note": "Collection does not exist"
                    }]
                }

            # Get index metadata info
            collection = Collection(collection_name, using=self.alias)
            index_metadata_exists = False
            index_info = None

            try:
                if hasattr(collection, 'indexes') and collection.indexes:
                    index_metadata_exists = True
                    index_info = collection.indexes[0].to_dict()
            except Exception:
                pass

            return {
                "status": "success",
                "operation": "get_load_state",
                "collection_name": collection_name,
                "load_state": load_state,
                "index_metadata_exists": index_metadata_exists,
                "index_info": index_info,
                "data": [{
                    "collection_name": collection_name,
                    "load_state": load_state,
                    "index_metadata_exists": index_metadata_exists,
                    "api": "utility.load_state (official only)"
                }]
            }
        except Exception as e:
            # If official API fails, return OBSERVATION/INFRA_FAILURE
            # Do NOT fall back to undocumented attributes
            return {
                "status": "error",
                "error": str(e),
                "operation": "get_load_state",
                "classification": "INFRA_FAILURE",
                "note": "Official API failed, no fallback available"
            }

    def _count_entities(self, params: Dict) -> Dict[str, Any]:
        """Count entities in storage.

        Returns ONLY:
        - storage_count: collection.num_entities (persistent storage count)
        - load_state: official utility.load_state() result

        Does NOT fabricate loaded_view_count. If loaded-view evidence is needed,
        use query/count(*) or search success/failure to observe.

        Args:
            params: Dict with keys:
                - collection_name (str): Collection name

        Returns:
            Response dict with storage count and load state
        """
        collection_name = params.get("collection_name")

        try:
            collection = Collection(collection_name, using=self.alias)

            # Get storage count (persistent)
            storage_count = collection.num_entities

            # Get official load state (convert LoadState enum to string)
            from pymilvus.client.types import LoadState
            load_state_raw = utility.load_state(collection_name, using=self.alias)
            load_state_map = {
                LoadState.NotLoad: "NotLoad",
                LoadState.Loaded: "Loaded",
                LoadState.Loading: "Loading",
                LoadState.NotExist: "NotExist"
            }
            load_state = load_state_map.get(load_state_raw, str(load_state_raw))

            return {
                "status": "success",
                "operation": "count_entities",
                "collection_name": collection_name,
                "storage_count": storage_count,
                "load_state": load_state,
                "data": [{
                    "storage_count": storage_count,
                    "load_state": load_state,
                    "note": "storage_count is persistent, load_state from official API"
                }]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "operation": "count_entities"
            }

    def _describe_collection(self, params: Dict) -> Dict[str, Any]:
        """Describe collection schema and metadata.

        Provides comprehensive schema information including:
        - Field names, types, and properties
        - Vector dimension
        - Entity count
        - Primary key field
        - Shard and partition information

        Args:
            params: Dict with keys:
                - collection_name (str): Name of collection to describe

        Returns:
            Response dict with:
                - status (str): "success" or "error"
                - operation (str): "describe_collection"
                - collection_name (str)
                - data (dict): {
                    - fields: List[Dict] with field info
                    - dimension: int
                    - entity_count: int
                    - primary_key: str
                    - num_shards: int
                    - consistency_level: int
                    - auto_id: bool
                }
        """
        collection_name = params.get("collection_name")

        try:
            collection = Collection(collection_name, using=self.alias)

            # Use describe() which returns comprehensive dict
            description = collection.describe()

            # Build field info from describe()["fields"]
            fields_info = []
            dimension = None
            primary_key = None

            for field in description["fields"]:
                field_info = {
                    "name": field["name"],
                    "type": field["type"].name,  # DataType enum has .name attribute
                    "is_primary": field.get("is_primary", False),
                    "field_id": field.get("field_id", None)
                }

                # Add type-specific params
                if "params" in field and field["params"]:
                    field_info["params"] = field["params"]
                    # Extract dimension for vector fields
                    if "dim" in field["params"]:
                        if dimension is None:  # First vector field
                            dimension = field["params"]["dim"]

                fields_info.append(field_info)

                # Track primary key
                if field.get("is_primary", False):
                    primary_key = field["name"]

            return {
                "status": "success",
                "operation": "describe_collection",
                "collection_name": collection_name,
                "data": [{
                    "fields": fields_info,
                    "dimension": dimension,
                    "entity_count": collection.num_entities,
                    "primary_key": primary_key,
                    "num_shards": description.get("num_shards", 1),
                    "consistency_level": description.get("consistency_level", 2),
                    "auto_id": description.get("auto_id", False),
                    "description": description.get("description", ""),
                    "properties": description.get("properties", {})
                }]
            }

        except Exception as e:
            return {
                "status": "error",
                "operation": "describe_collection",
                "collection_name": collection_name,
                "error": str(e)
            }

    def _flush(self, params: Dict) -> Dict[str, Any]:
        """Flush inserted data to persistent storage.

        Ensures data inserted via insert() is persisted and visible to
        subsequent queries and count operations.

        Args:
            params: Dict with keys:
                - collection_name (str): Collection name
                - async (bool): Whether to flush asynchronously (default False)

        Returns:
            Response dict with status and flush operation result
        """
        collection_name = params.get("collection_name")
        async_flush = params.get("async", False)

        try:
            collection = Collection(collection_name, using=self.alias)

            # Execute flush
            collection.flush(async_flush=async_flush)

            return {
                "status": "success",
                "operation": "flush",
                "collection_name": collection_name,
                "async": async_flush,
                "data": [{
                    "collection_name": collection_name,
                    "flushed": True,
                    "async": async_flush,
                    "note": "Data flushed to persistent storage"
                }]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "operation": "flush"
            }

    def _wait(self, params: Dict) -> Dict[str, Any]:
        """Wait for specified duration (for timing experiments).

        Args:
            params: Dict with keys:
                - duration_ms (int): Wait duration in milliseconds

        Returns:
            Response dict with status and actual wait time
        """
        import time

        duration_ms = params.get("duration_ms", 0)

        try:
            start_time = time.time()
            time.sleep(duration_ms / 1000.0)
            elapsed_ms = int((time.time() - start_time) * 1000)

            return {
                "status": "success",
                "operation": "wait",
                "duration_ms_requested": duration_ms,
                "duration_ms_actual": elapsed_ms,
                "data": [{
                    "waited_ms": elapsed_ms,
                    "requested_ms": duration_ms
                }]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "operation": "wait"
            }
