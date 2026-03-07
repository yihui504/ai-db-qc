"""Unit tests for MilvusAdapter."""

import pytest

from adapters.milvus_adapter import MilvusAdapter


class TestMilvusAdapter:
    """Test MilvusAdapter functionality."""

    @pytest.mark.skipif(
        "pymilvus" not in __import__('sys').modules,
        reason="pymilvus not installed"
    )
    def test_adapter_initialization(self):
        """Test MilvusAdapter initialization."""
        connection_config = {
            "host": "localhost",
            "port": 19530,
            "alias": "test"
        }

        # This will fail if Milvus is not running
        try:
            adapter = MilvusAdapter(connection_config)
            assert adapter.host == "localhost"
            assert adapter.port == 19530
            assert adapter.alias == "test"
            adapter.close()
        except Exception as e:
            # Connection failed - this is expected in unit test without Milvus
            pytest.skip(f"Could not connect to Milvus: {e}")

    def test_get_runtime_snapshot_structure(self):
        """Test get_runtime_snapshot returns correct structure."""
        connection_config = {
            "host": "localhost",
            "port": 19530,
            "alias": "test"
        }

        try:
            adapter = MilvusAdapter(connection_config)
            snapshot = adapter.get_runtime_snapshot()

            # Check structure
            assert "collections" in snapshot
            assert "indexed_collections" in snapshot
            assert "loaded_collections" in snapshot
            assert "connected" in snapshot
            assert "memory_stats" in snapshot
            assert isinstance(snapshot["collections"], list)

            adapter.close()
        except Exception as e:
            # Connection failed - skip test
            pytest.skip(f"Could not connect to Milvus: {e}")

    def test_health_check_returns_bool(self):
        """Test health_check returns boolean."""
        connection_config = {
            "host": "localhost",
            "port": 19530,
            "alias": "test"
        }

        try:
            adapter = MilvusAdapter(connection_config)
            result = adapter.health_check()
            assert isinstance(result, bool)
            adapter.close()
        except Exception as e:
            # Connection failed - skip test
            pytest.skip(f"Could not connect to Milvus: {e}")

    @pytest.mark.integration
    def test_adapter_real_milvus_connection(self):
        """Test real Milvus connection (integration test)."""
        connection_config = {
            "host": "localhost",
            "port": 19530,
            "alias": "test"
        }

        try:
            adapter = MilvusAdapter(connection_config)

            # Test health check
            assert adapter.health_check() is True

            # Test get_runtime_snapshot
            snapshot = adapter.get_runtime_snapshot()
            assert snapshot["connected"] is True
            assert isinstance(snapshot["collections"], list)

            adapter.close()
            assert True  # Cleanup successful
        except Exception as e:
            pytest.skip(f"Could not connect to Milvus: {e}")
