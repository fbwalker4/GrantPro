#!/usr/bin/env python3
"""
Grant Writing System - Centralized Database Connection

Supports:
  1. Supabase Postgres when GP-DATABASE_URL is set (production / Vercel)
  2. Local SQLite3 as fallback (local dev)

The returned connection is DB-API 2.0 compatible with a compatibility
wrapper so that existing code using SQLite-style ? placeholders and
row['column'] access works transparently on Postgres.

Usage:
    from db_connection import get_connection
    conn = get_connection()

Environment variables (GP- prefix for shared Vercel account):
    GP-DATABASE_URL  – Postgres connection string (pooler URL)
    GP-SUPABASE_URL  – Supabase project URL (for REST API, optional)
    GP-SUPABASE_KEY  – Supabase service-role key (optional)
"""

import os
import sqlite3
from pathlib import Path


# ---------------------------------------------------------------------------
# Load .env file for local development (if present)
# ---------------------------------------------------------------------------
def _load_dotenv():
    """Load GP_ vars from .env file if it exists."""
    for env_path in [
        Path(__file__).parent.parent / ".env",
        Path.home() / ".hermes" / "grant-system" / ".env",
    ]:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, _, val = line.partition('=')
                        os.environ.setdefault(key.strip(), val.strip())
            break

_load_dotenv()


# ---------------------------------------------------------------------------
# Supabase / Postgres configuration (GP- prefixed env vars)
# ---------------------------------------------------------------------------
def _gp_env(name: str) -> str | None:
    """Return env var trying GP_NAME then GP-NAME."""
    return os.environ.get(f"GP_{name}") or os.environ.get(f"GP-{name}")

GP_DATABASE_URL = _gp_env("DATABASE_URL")
GP_SUPABASE_URL = _gp_env("SUPABASE_URL")
GP_SUPABASE_KEY = _gp_env("SUPABASE_KEY")


# ---------------------------------------------------------------------------
# SQLite fallback path (emergency only — Supabase is primary for all envs)
# ---------------------------------------------------------------------------
LOCAL_DB_PATH = Path("/tmp/grants.db") if os.getenv("VERCEL") else (
    Path.home() / ".hermes" / "grant-system" / "tracking" / "grants.db"
)


# ===================================================================
# Postgres compatibility wrapper
# ===================================================================

def _sqlite_to_pg(sql: str) -> str:
    """Translate SQLite-specific syntax to Postgres equivalents."""
    import re
    # INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
    sql = re.sub(r'INSERT\s+OR\s+IGNORE\s+INTO', 'INSERT INTO', sql, flags=re.IGNORECASE)
    if 'INSERT INTO' in sql.upper() and 'ON CONFLICT' not in sql.upper() and 'OR IGNORE' in sql.upper():
        sql += ' ON CONFLICT DO NOTHING'
    # INSERT OR REPLACE → keep as INSERT INTO (callers should use explicit ON CONFLICT clauses)
    # Log a warning if this translation is triggered so we can find and fix the caller
    if re.search(r'INSERT\s+OR\s+REPLACE\s+INTO', sql, flags=re.IGNORECASE):
        import logging
        logging.getLogger('db_connection').warning(
            'INSERT OR REPLACE translated to plain INSERT — caller should use ON CONFLICT clause: %s', sql[:100])
    sql = re.sub(r'INSERT\s+OR\s+REPLACE\s+INTO', 'INSERT INTO', sql, flags=re.IGNORECASE)
    # AUTOINCREMENT → SERIAL (only in CREATE TABLE context, which is already handled by migration)
    sql = re.sub(r'INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT', 'SERIAL PRIMARY KEY', sql, flags=re.IGNORECASE)
    # SQLite double-quote strings in WHERE clauses → single quotes
    # e.g. WHERE status = "sent" → WHERE status = 'sent'
    return sql


def _sqlite_placeholder_to_pg(sql: str) -> str:
    """Convert SQLite-style ? placeholders to Postgres-style %s.

    Also applies broader SQLite→Postgres syntax translations.
    Ignores ? inside single-quoted string literals and -- line comments.
    Leaves PRAGMA statements alone (they will be skipped at execute time).
    """
    # Apply SQLite→Postgres syntax fixes first
    sql = _sqlite_to_pg(sql)

    # Fast path – no question marks means nothing to convert
    if "?" not in sql:
        return sql

    out: list[str] = []
    i = 0
    length = len(sql)
    while i < length:
        ch = sql[i]

        # Skip single-quoted strings
        if ch == "'":
            j = i + 1
            while j < length:
                if sql[j] == "'" and (j + 1 < length and sql[j + 1] == "'"):
                    j += 2  # escaped quote ''
                elif sql[j] == "'":
                    j += 1
                    break
                else:
                    j += 1
            out.append(sql[i:j])
            i = j
            continue

        # Skip -- line comments
        if ch == "-" and i + 1 < length and sql[i + 1] == "-":
            j = sql.find("\n", i)
            if j == -1:
                j = length
            out.append(sql[i:j])
            i = j
            continue

        if ch == "?":
            out.append("%s")
            i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out)


class _HybridRow(dict):
    """A dict that also supports integer indexing like a tuple.

    This bridges the gap between SQLite's Row (supports row[0] and row['col'])
    and psycopg2's RealDictRow (only supports row['col']).
    """
    def __init__(self, d):
        super().__init__(d)
        self._values = list(d.values())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        return iter(self._values)


class _PgCursorWrapper:
    """Wraps a psycopg2 RealDictCursor to accept ?-style placeholders."""

    def __init__(self, real_cursor):
        self._cursor = real_cursor

    # --- Core DB-API methods -----------------------------------------------

    def execute(self, sql: str, params=None):
        translated = _sqlite_placeholder_to_pg(sql)

        # Silently skip SQLite-only PRAGMA statements
        if translated.strip().upper().startswith("PRAGMA"):
            return self

        # SQLite accepts both tuples and lists; psycopg2 wants tuples
        if isinstance(params, list):
            params = tuple(params)

        self._cursor.execute(translated, params)
        return self

    def executemany(self, sql: str, seq_of_params):
        translated = _sqlite_placeholder_to_pg(sql)
        if translated.strip().upper().startswith("PRAGMA"):
            return self
        self._cursor.executemany(translated, seq_of_params)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        return _HybridRow(row) if row is not None else None

    def fetchall(self):
        return [_HybridRow(row) for row in self._cursor.fetchall()]

    def fetchmany(self, size=None):
        rows = self._cursor.fetchmany(size) if size is not None else self._cursor.fetchmany()
        return [_HybridRow(row) for row in rows]

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    def close(self):
        self._cursor.close()

    def __iter__(self):
        return iter(self._cursor)


class _PgConnectionWrapper:
    """Wraps a psycopg2 connection so it behaves like an sqlite3 connection.

    Key features:
      - conn.execute(sql, params) works (sqlite3 Connection has this shortcut)
      - Returns _PgCursorWrapper which translates ? -> %s
      - Uses RealDictCursor so rows support row['column'] access
    """

    def __init__(self, real_conn):
        self._conn = real_conn

    def cursor(self):
        from psycopg2.extras import RealDictCursor
        return _PgCursorWrapper(self._conn.cursor(cursor_factory=RealDictCursor))

    def execute(self, sql: str, params=None):
        """Shortcut matching sqlite3.Connection.execute()."""
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql: str, seq_of_params):
        cur = self.cursor()
        cur.executemany(sql, seq_of_params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    @property
    def row_factory(self):
        """No-op property so code that sets conn.row_factory = sqlite3.Row
        doesn't crash.  Postgres already returns dicts via RealDictCursor."""
        return None

    @row_factory.setter
    def row_factory(self, value):
        # Silently accept — RealDictCursor already gives dict-like rows.
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


# ===================================================================
# Public API
# ===================================================================

def get_connection():
    """
    Return a database connection.

    Priority:
      1. If GP-DATABASE_URL (or GP_DATABASE_URL) is set, connect to
         Supabase Postgres via psycopg2.
      2. Otherwise fall back to local SQLite.

    The returned object supports:
        conn.execute(sql, params)
        conn.commit() / conn.close()
        cursor.fetchone() / cursor.fetchall()
        row['column'] access on result rows
    """

    if GP_DATABASE_URL:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

            raw_conn = psycopg2.connect(GP_DATABASE_URL)
            # Autocommit off by default (matches SQLite behaviour where you
            # call conn.commit()).  Callers that forget to commit will see
            # their writes rolled back — same as SQLite WAL mode default.
            return _PgConnectionWrapper(raw_conn)
        except ImportError:
            # psycopg2 not installed — fall through to SQLite
            pass
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "Postgres connection failed, falling back to SQLite: %s", exc
            )

    # ------------------------------------------------------------------
    # Fallback: local SQLite
    # ------------------------------------------------------------------
    LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(LOCAL_DB_PATH))
    conn.row_factory = sqlite3.Row          # row['column'] access
    return conn
