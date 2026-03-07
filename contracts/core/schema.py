"""Core contract schema (database-agnostic)."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Dict, List, Optional

from schemas.common import OperationType


class ParameterConstraint(BaseModel):
    """Constraint on a parameter."""

    name: str
    type: str
    required: bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List] = None


class OperationContract(BaseModel):
    """Contract for a single operation."""

    operation_type: OperationType
    parameters: Dict[str, ParameterConstraint]
    required_preconditions: List[str] = Field(default_factory=list)


class CoreContract(BaseModel):
    """Core contract for database operations (database-agnostic)."""

    contract_name: str
    contract_version: str
    operations: Dict[OperationType, OperationContract]
