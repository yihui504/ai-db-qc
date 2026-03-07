"""Environment fingerprint capture for reproducibility."""

from __future__ import annotations

import platform
import socket
from datetime import datetime
from typing import Any, Dict

from schemas.evidence import Fingerprint


def capture_environment(connection_config: Dict[str, Any], adapter) -> Fingerprint:
    """Capture environment fingerprint.

    Args:
        connection_config: Database connection configuration
        adapter: Database adapter (must have health_check or similar)

    Returns:
        Fingerprint with environment and database info
    """
    import pymilvus
    from pymilvus import utility

    # Get Milvus version through adapter
    alias = connection_config.get("alias", "default")

    try:
        milvus_version = utility.get_server_version(using=alias)
    except Exception:
        milvus_version = "unknown"

    return Fingerprint(
        os=platform.platform(),
        python_version=platform.python_version(),
        pymilvus_version=pymilvus.__version__,
        milvus_version=milvus_version,
        hostname=socket.gethostname(),
        timestamp=datetime.now().isoformat(),
        db_config={
            "host": connection_config.get("host", "localhost"),
            "port": connection_config.get("port", 19530)
        }
    )
