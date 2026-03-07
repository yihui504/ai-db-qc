"""Unit tests for contracts."""

import pytest
from contracts.core.loader import get_default_contract
from contracts.core.validator import validate_contract, validate_profile_against_contract
from contracts.core.schema import CoreContract, ParameterConstraint, OperationContract
from contracts.db_profiles.loader import load_profile
from schemas.common import OperationType


def test_load_default_contract():
    """Test loading default contract."""
    contract = get_default_contract()
    assert contract.contract_name == "ai_db_core_v1"
    assert contract.contract_version == "1.0.0"
    assert len(contract.operations) == 9


def test_contract_search_operation():
    """Test search operation constraints."""
    contract = get_default_contract()
    search_op = contract.operations.get(OperationType.SEARCH)
    assert search_op is not None
    assert search_op.operation_type == OperationType.SEARCH

    # Check top_k constraint
    top_k_param = search_op.parameters.get("top_k")
    assert top_k_param is not None
    assert top_k_param.min_value == 1
    assert top_k_param.required is True

    # Check required preconditions
    assert "collection_exists" in search_op.required_preconditions
    assert "index_loaded" in search_op.required_preconditions
    assert len(search_op.required_preconditions) == 3


def test_contract_preconditions_are_list_of_strings():
    """Test that required_preconditions is a list of strings."""
    contract = get_default_contract()
    search_op = contract.operations.get(OperationType.SEARCH)
    assert isinstance(search_op.required_preconditions, list)
    assert all(isinstance(p, str) for p in search_op.required_preconditions)


def test_contract_create_collection():
    """Test create_collection operation."""
    contract = get_default_contract()
    create_op = contract.operations.get(OperationType.CREATE_COLLECTION)
    assert create_op is not None

    # dimension constraint
    dimension_param = create_op.parameters.get("dimension")
    assert dimension_param is not None
    assert dimension_param.min_value == 1

    # metric_type allowed values
    metric_param = create_op.parameters.get("metric_type")
    assert metric_param is not None
    assert metric_param.allowed_values == ["L2", "IP", "COSINE"]

    # No preconditions required for creation
    assert len(create_op.required_preconditions) == 0


def test_validate_contract_valid():
    """Test validator passes for valid contract."""
    contract = get_default_contract()
    errors = validate_contract(contract)
    assert len(errors) == 0


def test_validate_contract_checks_required_fields():
    """Test validator checks required top-level fields."""
    # Create invalid contract
    from contracts.core.schema import CoreContract, OperationContract

    invalid_contract = CoreContract(
        contract_name="",  # Empty
        contract_version="",  # Empty
        operations={}  # Empty
    )

    errors = validate_contract(invalid_contract)
    assert len(errors) >= 3
    assert any("contract_name" in e for e in errors)
    assert any("contract_version" in e for e in errors)
    assert any("operations" in e for e in errors)


def test_validate_contract_checks_preconditions_format():
    """Test validator checks required_preconditions format (semantic checks)."""
    # Note: pydantic already validates structure (list of strings)
    # Our validator does semantic checks like empty strings
    # We need to bypass pydantic to test the validator directly

    # Create operation with empty precondition string
    # (pydantic allows this, but our validator catches it)
    invalid_op = OperationContract(
        operation_type=OperationType.SEARCH,
        parameters={},
        required_preconditions=["valid_precond", "", "   "]  # Empty/whitespace strings
    )

    invalid_contract = CoreContract(
        contract_name="test",
        contract_version="1.0",
        operations={OperationType.SEARCH: invalid_op}
    )

    errors = validate_contract(invalid_contract)
    assert len(errors) > 0
    assert any("empty string" in e for e in errors)


def test_validate_contract_checks_parameter_constraints():
    """Test validator checks parameter constraint structure."""
    # Create parameter with missing name
    invalid_param = ParameterConstraint(
        name="",  # Empty name
        type="",  # Empty type
        required=True,
        min_value=10,
        max_value=5  # min > max
    )

    invalid_op = OperationContract(
        operation_type=OperationType.SEARCH,
        parameters={"top_k": invalid_param},
        required_preconditions=[]
    )

    invalid_contract = CoreContract(
        contract_name="test",
        contract_version="1.0",
        operations={OperationType.SEARCH: invalid_op}
    )

    errors = validate_contract(invalid_contract)
    assert len(errors) > 0
    assert any("name is required" in e for e in errors)
    assert any("type is required" in e for e in errors)
    assert any("min_value" in e and "max_value" in e for e in errors)


def test_validate_profile_against_contract():
    """Test profile validation against core contract."""
    contract = get_default_contract()
    profile = load_profile("contracts/db_profiles/milvus_profile.yaml")

    errors = validate_profile_against_contract(profile, contract)
    assert len(errors) == 0, f"Expected no errors, got: {errors}"


def test_validate_profile_with_invalid_operation_reference():
    """Test profile validation catches invalid operation references."""
    from contracts.db_profiles.schema import DBProfile

    # Create profile with invalid operation reference
    invalid_profile = DBProfile(
        profile_name="test",
        db_type="test",
        supported_operations=["create_collection", "nonexistent_operation"],
        operation_mappings={}
    )

    contract = get_default_contract()
    errors = validate_profile_against_contract(invalid_profile, contract)

    assert len(errors) > 0
    assert any("nonexistent_operation" in e for e in errors)
