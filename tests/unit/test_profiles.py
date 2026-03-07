"""Unit tests for DB profiles."""

import pytest
from contracts.db_profiles.loader import load_profile
from contracts.db_profiles.schema import DBProfile


def test_load_milvus_profile():
    """Test loading Milvus profile."""
    profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
    assert profile.profile_name == "milvus-2.3"
    assert profile.db_type == "milvus"
    assert profile.db_version == "2.3.x"


def test_db_profile_has_all_required_fields():
    """Test DBProfile has all required fields."""
    profile = load_profile("contracts/db_profiles/milvus_profile.yaml")

    # Check all fields exist and are populated
    assert hasattr(profile, "supported_operations")
    assert hasattr(profile, "operation_mappings")
    assert hasattr(profile, "parameter_relaxations")
    assert hasattr(profile, "supported_features")
    assert hasattr(profile, "environment_requirements")

    # Check content exists
    assert len(profile.supported_operations) > 0
    assert len(profile.supported_features) > 0


def test_milvus_supported_operations():
    """Test Milvus supported operations."""
    profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
    assert "create_collection" in profile.supported_operations
    assert "insert" in profile.supported_operations
    assert "search" in profile.supported_operations
    assert len(profile.supported_operations) == 9


def test_milvus_supported_features():
    """Test Milvus supported features."""
    profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
    assert "IVF_FLAT" in profile.supported_features
    assert "HNSW" in profile.supported_features
    assert "FILTERED_SEARCH" in profile.supported_features


def test_milvus_parameter_relaxations():
    """Test Milvus parameter relaxations."""
    profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
    assert "search" in profile.parameter_relaxations
    assert "top_k" in profile.parameter_relaxations["search"]
    assert profile.parameter_relaxations["search"]["top_k"]["max_value"] == 16384


def test_milvus_operation_mappings():
    """Test Milvus operation mappings."""
    profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
    assert "search" in profile.operation_mappings
    search_mapping = profile.operation_mappings["search"]
    assert search_mapping["db_operation"] == "search"
    assert "/collections/" in search_mapping["api_endpoint"]


def test_milvus_environment_requirements():
    """Test Milvus environment requirements."""
    profile = load_profile("contracts/db_profiles/milvus_profile.yaml")
    assert "service" in profile.environment_requirements
    assert "min_memory" in profile.environment_requirements
