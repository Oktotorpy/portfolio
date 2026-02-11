import sqlite3
import os
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "portfolio.db"))
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    db_exists = os.path.exists(DB_PATH)
    conn = get_db()
    if not db_exists:
        with open(SCHEMA_PATH) as f:
            conn.executescript(f.read())
    conn.close()
