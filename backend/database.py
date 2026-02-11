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
    else:
        _migrate(conn)
    conn.close()


def _table_exists(conn, name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _column_exists(conn, table, column):
    cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    return column in cols


def _migrate(conn):
    """Add missing tables/columns to existing databases."""

    # --- jobs.color ---
    if not _column_exists(conn, "jobs", "color"):
        conn.execute("ALTER TABLE jobs ADD COLUMN color TEXT DEFAULT '#3a3d48'")

    # --- roles.department ---
    if not _column_exists(conn, "roles", "department"):
        conn.execute("ALTER TABLE roles ADD COLUMN department TEXT DEFAULT ''")

    # --- tools lookup table ---
    if not _table_exists(conn, "tools"):
        conn.executescript("""
            CREATE TABLE tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            INSERT OR IGNORE INTO tools (name) VALUES ('Claude'), ('Premiere'), ('Photoshop');
        """)

    # --- weights lookup table ---
    if not _table_exists(conn, "weights"):
        conn.executescript("""
            CREATE TABLE weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            INSERT OR IGNORE INTO weights (name) VALUES
                ('Small'), ('Medium'), ('Big'), ('Landmark'), ('Continuous');
        """)

    # --- projects.weight_id ---
    if not _column_exists(conn, "projects", "weight_id"):
        conn.execute("ALTER TABLE projects ADD COLUMN weight_id INTEGER DEFAULT NULL REFERENCES weights(id) ON DELETE SET NULL")

    # --- project_tools junction ---
    if not _table_exists(conn, "project_tools"):
        conn.execute("""
            CREATE TABLE project_tools (
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                tool_id INTEGER NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
                PRIMARY KEY (project_id, tool_id)
            )
        """)

    # --- project_media table ---
    if not _table_exists(conn, "project_media"):
        conn.execute("""
            CREATE TABLE project_media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                media_type TEXT NOT NULL CHECK (media_type IN ('image', 'video', 'youtube')),
                media_value TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0
            )
        """)
        # Migrate existing single-content to project_media
        rows = conn.execute(
            "SELECT id, content_type, content_value FROM projects WHERE content_type IS NOT NULL AND content_value IS NOT NULL AND content_value != ''"
        ).fetchall()
        for row in rows:
            conn.execute(
                "INSERT INTO project_media (project_id, media_type, media_value, sort_order) VALUES (?, ?, ?, 0)",
                (row[0], row[1], row[2])
            )

    conn.commit()
