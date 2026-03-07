"""Static validation of contracts and profiles."""

from __future__ import annotations

from contracts.core.schema import CoreContract, OperationContract, ParameterConstraint
from contracts.db_profiles.schema import DBProfile
from schemas.common import OperationType


class ContractValidationError(Exception):
    pass


def validate_contract(contract: CoreContract) -> list[str]:
    """
    Perform static validation on loaded contract.
    Returns list of error messages (empty if valid).
    """
    errors = []

    # Check required top-level fields
    if not contract.contract_name:
        errors.append("contract_name is required")
    if not contract.contract_version:
        errors.append("contract_version is required")
    if not contract.operations:
        errors.append("operations must not be empty")

    # Check operation references consistency
    for op_type, op_contract in contract.operations.items():
        if not isinstance(op_type, OperationType):
            errors.append(f"Invalid operation type: {op_type}")
            continue

        # Check operation contract structure
        op_errors = _validate_operation_contract(op_type, op_contract)
        errors.extend(op_errors)

    return errors


def _validate_operation_contract(op_type: OperationType, op_contract: OperationContract) -> list[str]:
    """Validate a single operation contract."""
    errors = []

    # Check required_preconditions format (list of strings)
    if not isinstance(op_contract.required_preconditions, list):
        errors.append(f"{op_type}: required_preconditions must be a list")
    else:
        for i, precond in enumerate(op_contract.required_preconditions):
            if not isinstance(precond, str):
                errors.append(f"{op_type}: required_preconditions[{i}] must be string, got {type(precond).__name__}")
            elif not precond.strip():
                errors.append(f"{op_type}: required_preconditions[{i}] is empty string")

    # Check parameters structure
    if not isinstance(op_contract.parameters, dict):
        errors.append(f"{op_type}: parameters must be a dict")
    else:
        for param_name, param_constraint in op_contract.parameters.items():
            param_errors = _validate_parameter_constraint(op_type, param_name, param_constraint)
            errors.extend(param_errors)

    return errors


def _validate_parameter_constraint(op_type: OperationType, param_name: str, constraint: ParameterConstraint) -> list[str]:
    """Validate a parameter constraint."""
    errors = []

    # Check required fields exist
    if not constraint.name:
        errors.append(f"{op_type}.parameters.{param_name}: name is required")
    if not constraint.type:
        errors.append(f"{op_type}.parameters.{param_name}: type is required")

    # Check numeric constraint consistency
    if constraint.min_value is not None and constraint.max_value is not None:
        if constraint.min_value > constraint.max_value:
            errors.append(f"{op_type}.parameters.{param_name}: min_value ({constraint.min_value}) > max_value ({constraint.max_value})")

    # Check allowed_values is a list if present
    if constraint.allowed_values is not None:
        if not isinstance(constraint.allowed_values, list):
            errors.append(f"{op_type}.parameters.{param_name}: allowed_values must be a list")

    return errors


def validate_profile_against_contract(profile: DBProfile, contract: CoreContract) -> list[str]:
    """
    Validate that profile operation references exist in core contract.
    Returns list of error messages (empty if valid).
    """
    errors = []

    # Check supported_operations exist in contract
    contract_ops = set(contract.operations.keys())
    for op_name in profile.supported_operations:
        if op_name not in contract_ops:
            errors.append(f"profile.supported_operations: '{op_name}' not defined in core contract")

    # Check operation_mappings reference valid operations
    for op_name in profile.operation_mappings.keys():
        if op_name not in contract_ops:
            errors.append(f"profile.operation_mappings: '{op_name}' not defined in core contract")

    return errors
