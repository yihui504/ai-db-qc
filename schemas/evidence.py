"""Evidence schemas for environment and runtime snapshots."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List


class Fingerprint(BaseModel):
    """Environment fingerprint for reproducibility."""

    os: str = Field(description="Operating system platform")
    python_version: str = Field(description="Python version")
    pymilvus_version: str = Field(description="pymilvus library version")
    milvus_version: str = Field(description="Milvus server version")
    hostname: str = Field(description="Machine hostname")
    timestamp: str = Field(description="ISO timestamp of capture")
    db_config: Dict[str, Any] = Field(default_factory=dict, description="Database connection config")


class RuntimeSnapshot(BaseModel):
    """Runtime snapshot of database state."""

    collections: List[str] = Field(default_factory=list, description="Available collections")
    indexed_collections: List[str] = Field(default_factory=list, description="Collections with indexes")
    loaded_collections: List[str] = Field(default_factory=list, description="Collections loaded into memory")
    connected: bool = Field(default=True, description="Whether database is connected")
    memory_stats: Dict[str, Any] = Field(default_factory=dict, description="Memory usage statistics")
    snapshot_id: str = Field(default="", description="Unique ID for this snapshot")
    timestamp: str = Field(default="", description="ISO timestamp of snapshot")
