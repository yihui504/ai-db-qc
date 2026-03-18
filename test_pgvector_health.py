"""Test pgvector health check."""
import sys
sys.path.insert(0, ".")

from adapters.pgvector_adapter import PgvectorAdapter

adapter = PgvectorAdapter({
    "container": "pgvector",
    "database": "vectordb",
    "user": "postgres",
    "password": "pgvector",
})

print(f"Pgvector health check: {adapter.health_check()}")

# Try to list tables
result = adapter.execute({"operation": "list_collections", "params": {}})
print(f"List collections: {result}")
