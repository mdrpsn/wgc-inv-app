import sqlite3
from pathlib import Path

DB_PATH = Path("inventory.db")

SCHEMA_FILES = [
    "schema.sql",
    "schema_multilocation.sql",
]

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")

try:
    for schema_file in SCHEMA_FILES:
        path = Path(schema_file)

        if not path.exists():
            print(f"SKIP: {schema_file} not found.")
            continue

        print(f"Applying {schema_file}...")
        conn.executescript(path.read_text(encoding="utf-8"))

    conn.commit()

    tables = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    print("")
    print("Tables now in inventory.db:")
    for table in tables:
        print(f"  - {table['name']}")

    required_tables = {
        "suppliers",
        "products",
        "purchase_orders",
        "purchase_order_items",
        "locations",
        "item_requests",
        "item_request_items",
        "stock_transfers",
        "stock_transfer_items",
        "stock_movements",
    }

    existing_tables = {table["name"] for table in tables}
    missing_tables = sorted(required_tables - existing_tables)

    print("")

    if missing_tables:
        print("FAIL: Missing required tables:")
        for table in missing_tables:
            print(f"  - {table}")
        raise SystemExit(1)

    print("PASS: Required tables exist.")

except Exception as exc:
    conn.rollback()
    print("")
    print("FAIL: Schema apply failed.")
    print(exc)
    raise

finally:
    conn.close()
