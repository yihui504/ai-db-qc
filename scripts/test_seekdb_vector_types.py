"""Test different vector column type syntaxes for seekdb."""

import pymysql

conn = pymysql.connect(
    host="127.0.0.1",
    port=2881,
    user="root",
    password="",
    database="test",
    charset='utf8mb4'
)
cursor = conn.cursor()

# Test different vector type syntaxes
vector_types = [
    "VECTOR(3)",
    "VEC(3)",
    "VECTOR FLOAT(3)",
    "FLOAT VECTOR(3)",
    "ARRAY(3)",
    "VECF32(3)",
]

print("Testing vector column type syntaxes...")
for vtype in vector_types:
    try:
        cursor.execute(f"DROP TABLE IF EXISTS test_vector_type")
        cursor.execute(f"CREATE TABLE test_vector_type (id INT, vec {vtype})")
        print(f"[OK] {vtype} works!")
        cursor.execute("DROP TABLE test_vector_type")
        break
    except Exception as e:
        print(f"[FAIL] {vtype}: {str(e)[:80]}")

cursor.close()
conn.close()
