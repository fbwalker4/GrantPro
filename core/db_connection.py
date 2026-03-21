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

# Default local path used by all existing modules
LOCAL_DB_PATH = Path.home() / ".hermes" / "grant-system" / "tracking" / "grants.db"

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
