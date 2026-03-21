#!/usr/bin/env python3
"""
Grant Writing System - Centralized Database Connection

Supports:
  1. Turso (libsql) when TURSO_DATABASE_URL and TURSO_AUTH_TOKEN are set
  2. Local SQLite3 as fallback

Usage:
    from db_connection import get_connection
    conn = get_connection()
"""

import os
import sqlite3
from pathlib import Path

# Database path: configurable via DATABASE_PATH env var
# Defaults to ~/.hermes/grant-system/tracking/grants.db locally
# On Vercel (serverless), use /tmp/grants.db
_default_path = Path.home() / ".hermes" / "grant-system" / "tracking" / "grants.db"
_env_path = os.getenv("DATABASE_PATH")
if _env_path:
    LOCAL_DB_PATH = Path(_env_path)
elif os.getenv("VERCEL"):
    LOCAL_DB_PATH = Path("/tmp/grants.db")
else:
    LOCAL_DB_PATH = _default_path

# Turso / libsql configuration
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")


def get_connection():
    """
    Return a database connection.

    If TURSO_DATABASE_URL and TURSO_AUTH_TOKEN environment variables are set,
    attempt to connect via libsql_experimental (Turso's Python SDK).
    Falls back to local sqlite3 if libsql is unavailable or env vars are missing.
    """
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        try:
            import libsql_experimental as libsql
            conn = libsql.connect(
                TURSO_DATABASE_URL,
                auth_token=TURSO_AUTH_TOKEN,
            )
            return conn
        except ImportError:
            # libsql not installed -- fall back to local SQLite
            pass
        except Exception:
            # Connection failed -- fall back to local SQLite
            pass

    # Ensure the directory exists for local SQLite
    LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(LOCAL_DB_PATH))
    return conn
