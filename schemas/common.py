"""Common types and enums used across schemas."""

from __future__ import annotations

from enum import Enum
from typing import Literal
from pydantic import BaseModel


class InputValidity(str, Enum):
    """Whether input satisfies abstract contract constraints."""

    LEGAL = "legal"
    ILLEGAL = "illegal"


class BugType(str, Enum):
    """The four-type defect classification."""

    TYPE_1 = "type-1"
    TYPE_2 = "type-2"
    TYPE_2_PRECONDITION_FAILED = "type-2.precondition_failed"  # Subtype of Type-2
    TYPE_3 = "type-3"
    TYPE_4 = "type-4"


class OperationType(str, Enum):
    """Supported database operations."""

    CREATE_COLLECTION = "create_collection"
    DROP_COLLECTION = "drop_collection"
    INSERT = "insert"
    DELETE = "delete"
    BUILD_INDEX = "build_index"
    LOAD_INDEX = "load_index"
    SEARCH = "search"
    FILTERED_SEARCH = "filtered_search"
    HYBRID_SEARCH = "hybrid_search"


class ObservedOutcome(str, Enum):
    """What actually happened during execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    CRASH = "crash"
    HANG = "hang"
    TIMEOUT = "timeout"


class GateTrace(BaseModel):
    """Trace of precondition evaluation.

    check_type distinguishes:
    - "legality": Abstract contract compliance (operation exists, params defined)
    - "runtime": Runtime readiness (collection exists, connection active)
    """

    precondition_name: str
    check_type: Literal["legality", "runtime"] = "legality"
    passed: bool
    reason: str = ""
