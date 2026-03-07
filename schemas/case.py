"""Test case schema."""

from pydantic import BaseModel, Field
from typing import Dict, Any, List

from schemas.common import InputValidity, OperationType


class TestCase(BaseModel):
    """A test case for database quality assurance."""

    case_id: str
    operation: OperationType
    params: Dict[str, Any]
    expected_validity: InputValidity
    required_preconditions: List[str] = Field(
        default_factory=list,
        description="Runtime preconditions required (extensible, e.g., 'collection_exists', 'index_loaded')"
    )
    oracle_refs: List[str] = Field(default_factory=list)
    rationale: str = ""
