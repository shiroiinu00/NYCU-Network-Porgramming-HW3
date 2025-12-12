import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "store.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row
    # activate foreign key
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    schema_path = Path(__file__).parent / "schema.sql"
    with get_connection() as conn:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)

        