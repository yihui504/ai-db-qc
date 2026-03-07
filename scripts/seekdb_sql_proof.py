"""Minimal seekdb SQL connectivity proof.

Before rewriting the full adapter, prove we can:
1. Connect to seekdb via MySQL protocol
2. Create a table with vector column
3. Insert rows with vectors
4. Run vector search query

This is a one-off proof, not production code.

Usage:
    python scripts/seekdb_sql_proof.py --host 127.0.0.1 --port 2881 --user root --password ""
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="seekdb SQL connectivity proof")
    parser.add_argument("--host", default="127.0.0.1", help="seekdb host")
    parser.add_argument("--port", default="2881", help="seekdb SQL port")
    parser.add_argument("--user", default="root", help="MySQL user")
    parser.add_argument("--password", default="", help="MySQL password")
    parser.add_argument("--database", default="test", help="Database name")

    args = parser.parse_args()

    print("=" * 60)
    print("  seekdb SQL Connectivity Proof")
    print("=" * 60)
    print(f"Target: {args.user}@{args.host}:{args.port}")
    print()

    # Try to import MySQL client
    try:
        import pymysql
        print("[OK] Using PyMySQL as MySQL client")
    except ImportError:
        try:
            import mysql.connector as mysql_client
            print("[OK] Using mysql-connector-python as MySQL client")
            pymysql = None
        except ImportError:
            print("[ERROR] No MySQL client library found")
            print()
            print("Please install one of:")
            print("  pip install pymysql")
            print("  pip install mysql-connector-python")
            return 1

    # Step 1: Connect
    print()
    print("Step 1: Connecting to seekdb...")
    try:
        if pymysql:
            conn = pymysql.connect(
                host=args.host,
                port=int(args.port),
                user=args.user,
                password=args.password,
                database=args.database,
                charset='utf8mb4'
            )
        else:
            conn = mysql_client.connect(
                host=args.host,
                port=int(args.port),
                user=args.user,
                password=args.password,
                database=args.database,
                charset='utf8mb4'
            )
        cursor = conn.cursor()
        print(f"[OK] Connected successfully")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("  - Is seekdb Docker container running?")
        print(f"    docker run -d -p {args.port}:2881 oceanbase/seekdb")
        print("  - Did you wait for seekdb to fully start (may take 30-60s)?")
        print("  - Is the port correct?")
        return 1

    # Step 2: Create test table with vector column
    print()
    print("Step 2: Creating table with vector column...")
    try:
        # seekdb uses VECTOR(N) for vector columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proof_test (
                id INT PRIMARY KEY,
                embedding VECTOR(3),
                name VARCHAR(100)
            )
        """)
        conn.commit()
        print("[OK] Table created: proof_test (id, embedding VECTOR(3), name)")
    except Exception as e:
        print(f"[ERROR] Table creation failed: {e}")
        print("This might mean seekdb is not fully initialized yet")
        return 1

    # Clean up any existing data
    cursor.execute("DELETE FROM proof_test")
    conn.commit()

    # Step 3: Insert rows with vectors
    print()
    print("Step 3: Inserting test rows...")
    try:
        # seekdb vector syntax: '[x, y, z]' as string
        test_data = [
            (1, '[0.1, 0.2, 0.3]', 'item_a'),
            (2, '[0.4, 0.5, 0.6]', 'item_b'),
            (3, '[0.7, 0.8, 0.9]', 'item_c'),
        ]

        for row_id, vec, name in test_data:
            cursor.execute(
                "INSERT INTO proof_test (id, embedding, name) VALUES (%s, %s, %s)",
                (row_id, vec, name)
            )
        conn.commit()
        print(f"[OK] Inserted {len(test_data)} rows")
    except Exception as e:
        print(f"[ERROR] Insert failed: {e}")
        return 1

    # Step 4: Verify insert
    print()
    print("Step 4: Verifying inserts...")
    try:
        cursor.execute("SELECT id, name FROM proof_test ORDER BY id")
        rows = cursor.fetchall()
        print(f"[OK] Found {len(rows)} rows:")
        for row_id, name in rows:
            print(f"    - {row_id}: {name}")
    except Exception as e:
        print(f"[ERROR] Verification failed: {e}")
        return 1

    # Step 5: Vector search query
    print()
    print("Step 5: Running vector search...")
    try:
        # seekdb uses l2_distance() for vector distance
        query_vector = '[0.15, 0.25, 0.35]'  # Closest to item_a

        cursor.execute("""
            SELECT id, name,
                   l2_distance(embedding, %s) AS distance
            FROM proof_test
            ORDER BY distance
            LIMIT 2
        """, (query_vector,))

        results = cursor.fetchall()
        print(f"[OK] Search returned {len(results)} results:")
        for i, (row_id, name, distance) in enumerate(results):
            print(f"    [{i}] id={row_id}, name={name}, distance={distance:.4f}")

        # Verify nearest neighbor is item_a (id=1)
        if results and results[0][0] == 1:
            print("[OK] Correct nearest neighbor: item_a")
        else:
            print("[WARN] Unexpected nearest neighbor")

    except Exception as e:
        print(f"[ERROR] Vector search failed: {e}")
        print("This might indicate:")
        print("  - Different distance function name")
        print("  - Different vector literal syntax")
        print("  - seekdb version differences")
        return 1

    # Step 6: Cleanup
    print()
    print("Step 6: Cleanup...")
    try:
        cursor.execute("DROP TABLE IF EXISTS proof_test")
        conn.commit()
        print("[OK] Dropped test table")
    except Exception as e:
        print(f"[WARN] Cleanup warning: {e}")

    cursor.close()
    conn.close()

    print()
    print("=" * 60)
    print("[OK] CONNECTIVITY PROOF PASSED")
    print("=" * 60)
    print()
    print("Confirmed seekdb SQL features:")
    print("  - Vector column type: VECTOR(N)")
    print("  - Vector literal: '[x, y, z]'")
    print("  - Distance function: l2_distance(vector, query)")
    print("  - Vector search: SELECT ... ORDER BY l2_distance(...) LIMIT k")
    print()
    print("-> Ready to proceed with full adapter rewrite")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
