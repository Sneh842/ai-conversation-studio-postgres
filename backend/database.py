"""
PostgreSQL database layer for AI Conversation Studio.

Swapped from SQLite (see README "Future Enhancements") for concurrent
multi-user access. This module is a drop-in replacement: it keeps the exact
same call pattern used throughout the codebase -
    with db() as conn:
        conn.execute("SELECT * FROM x WHERE id = ?", (id,))
        cur = conn.execute("INSERT INTO x (...) VALUES (?, ?)", (a, b))
        new_id = cur.lastrowid
- so no other backend file (main.py, knowledge.py, seed_data.py) needed to
change. It translates `?` placeholders to psycopg2's `%s`, translates the
SQLite `datetime('now')` call to Postgres `NOW()`, and emulates
`cursor.lastrowid` via `INSERT ... RETURNING id`.

Configure the connection with a DATABASE_URL environment variable, e.g.:
    postgresql://studio_user:studio_pass@localhost:5432/ai_conversation_studio
See .env.example.
"""
import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ai_conversation_studio",
)


class _CursorWrapper:
    """Wraps a psycopg2 RealDictCursor to keep the sqlite3-style call
    pattern (`?` placeholders, `cur.lastrowid`) used across the codebase."""

    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None

    def execute(self, sql, params=()):
        pg_sql = sql.replace("?", "%s").replace("datetime('now')", "NOW()")
        stripped = pg_sql.strip().upper()

        if stripped.startswith("INSERT") and "RETURNING" not in stripped:
            pg_sql = pg_sql.rstrip().rstrip(";") + " RETURNING id"
            self._cursor.execute(pg_sql, params)
            row = self._cursor.fetchone()
            self.lastrowid = row["id"] if row else None
        else:
            self._cursor.execute(pg_sql, params)

        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()


class _ConnectionWrapper:
    """Wraps a psycopg2 connection so `conn.execute(...)` works directly,
    matching how sqlite3.Connection is used elsewhere in this project."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        cursor = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return _CursorWrapper(cursor).execute(sql, params)

    def executescript(self, sql):
        with self._conn.cursor() as cur:
            cur.execute(sql)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return _ConnectionWrapper(conn)


@contextmanager
def db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS knowledge_sources (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS assistants (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                persona TEXT NOT NULL,
                hallucination_bias REAL DEFAULT 0.15
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                assistant_id INTEGER REFERENCES assistants(id),
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                used_source_ids TEXT,
                generation_mode TEXT DEFAULT 'mock',
                generation_error TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS evaluations (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER REFERENCES conversations(id),
                relevance_score REAL,
                groundedness_score REAL,
                hallucination_risk REAL,
                overall_score REAL,
                explanation TEXT,
                flagged INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER REFERENCES conversations(id),
                rating TEXT NOT NULL,
                comment TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS governance_reviews (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER REFERENCES conversations(id),
                status TEXT DEFAULT 'pending',
                reviewer_note TEXT,
                reviewed_at TIMESTAMP
            );
            """
        )

        # Safe migration for DBs created before generation_mode existed
        with conn._conn.cursor() as cur:
            cur.execute(
                """SELECT column_name FROM information_schema.columns
                   WHERE table_name = 'conversations'"""
            )
            existing_cols = [r[0] for r in cur.fetchall()]

        if "generation_mode" not in existing_cols:
            conn.execute("ALTER TABLE conversations ADD COLUMN generation_mode TEXT DEFAULT 'mock'")
        if "generation_error" not in existing_cols:
            conn.execute("ALTER TABLE conversations ADD COLUMN generation_error TEXT")


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows):
    return [dict(r) for r in rows]
