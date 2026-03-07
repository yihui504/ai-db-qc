"""DB profile schema (database-specific)."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Dict, List, Any


class DBProfile(BaseModel):
    """Database-specific profile."""

    profile_name: str
    db_type: str
    db_version: str = ""
    description: str = ""

    # Operation support
    supported_operations: List[str] = Field(default_factory=list)

    # Operation mappings (core op -> DB-specific API)
    operation_mappings: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    # Parameter relaxations (override core constraints)
    parameter_relaxations: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Key: operation_name, value: {param: {min/max/allowed}}"
    )

    # Supported features
    supported_features: List[str] = Field(
        default_factory=list,
        description="e.g., IVF_FLAT, HNSW, scalar_index"
    )

    # Environment requirements
    environment_requirements: Dict[str, str] = Field(
        default_factory=dict,
        description="e.g., min_memory, service_dependencies"
    )
