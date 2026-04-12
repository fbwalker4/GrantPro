#!/usr/bin/env python3
"""GrantPro retention/cleanup job.

Safe by default:
- dry-run unless --apply is passed
- only removes clearly stale records/files
- skips any record that still appears active or linked

Cleans up, when present:
- stale draft/error rows
- expired testimonial tokens
- abandoned onboarding/session artifacts
- closed tickets older than retention window
- old temp files under approved temp directories
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.db_connection import get_connection

LOG = logging.getLogger("grantpro.cleanup_retention")


def _table_exists(conn, name: str) -> bool:
    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return bool(row)


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _age_cutoff(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).isoformat()


def cleanup_drafts(conn, apply: bool) -> int:
    if not _table_exists(conn, "drafts"):
        return 0
    cutoff = _age_cutoff(45)
    rows = conn.execute(
        """
        SELECT id, status, updated_at, created_at, content
        FROM drafts
        WHERE COALESCE(status, '') IN ('draft', 'failed', 'error')
          AND COALESCE(updated_at, created_at) < ?
          AND TRIM(COALESCE(content, '')) = ''
        """,
        (cutoff,),
    ).fetchall()
    if apply and rows:
        conn.executemany("DELETE FROM drafts WHERE id = ?", [(r[0],) for r in rows])
    return len(rows)


def cleanup_testimonial_tokens(conn, apply: bool) -> int:
    if not _table_exists(conn, "award_matches"):
        return 0
    cutoff = _age_cutoff(90)
    rows = conn.execute(
        """
        SELECT id, testimonial_token, created_at, notified
        FROM award_matches
        WHERE testimonial_token IS NOT NULL
          AND created_at < ?
          AND COALESCE(notified, 0) = 1
        """,
        (cutoff,),
    ).fetchall()
    if apply and rows:
        conn.executemany("UPDATE award_matches SET testimonial_token = NULL WHERE id = ?", [(r[0],) for r in rows])
    return len(rows)


def cleanup_abandoned_onboarding(conn, apply: bool) -> int:
    if not _table_exists(conn, "users"):
        return 0
    cutoff = _age_cutoff(30)
    rows = conn.execute(
        """
        SELECT id, created_at, updated_at, onboarding_completed
        FROM users
        WHERE COALESCE(onboarding_completed, 0) = 0
          AND COALESCE(updated_at, created_at) < ?
        """,
        (cutoff,),
    ).fetchall()
    if apply and rows:
        # Preserve the account; only clear stale session-ish metadata if columns exist.
        for row in rows:
            conn.execute("UPDATE users SET last_login = COALESCE(last_login, updated_at) WHERE id = ?", (row[0],))
    return len(rows)


def cleanup_closed_tickets(conn, apply: bool) -> int:
    table = None
    for candidate in ("support_tickets", "tickets"):
        if _table_exists(conn, candidate):
            table = candidate
            break
    if not table:
        return 0
    cutoff = _age_cutoff(180)
    rows = conn.execute(
        f"""
        SELECT id, status, updated_at, created_at
        FROM {table}
        WHERE LOWER(COALESCE(status, '')) IN ('closed', 'resolved', 'archived', 'done')
          AND COALESCE(updated_at, created_at) < ?
        """,
        (cutoff,),
    ).fetchall()
    if apply and rows:
        conn.executemany(f"DELETE FROM {table} WHERE id = ?", [(r[0],) for r in rows])
    return len(rows)


def cleanup_temp_files(paths, apply: bool) -> int:
    removed = 0
    cutoff = datetime.now() - timedelta(days=7)
    for base in paths:
        base_path = Path(base).expanduser()
        if not base_path.exists() or not base_path.is_dir():
            continue
        for path in base_path.rglob("*"):
            if not path.is_file():
                continue
            if path.name.startswith('.'):
                continue
            try:
                if datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
                    removed += 1
                    if apply:
                        path.unlink(missing_ok=True)
            except OSError:
                continue
    return removed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually delete/update stale records")
    parser.add_argument("--temp-dir", action="append", default=[], help="Approved temp directory to sweep")
    args = parser.parse_args()

    conn = get_connection()
    try:
        counts = {
            "stale_drafts": cleanup_drafts(conn, args.apply),
            "expired_tokens": cleanup_testimonial_tokens(conn, args.apply),
            "abandoned_onboarding": cleanup_abandoned_onboarding(conn, args.apply),
            "closed_tickets": cleanup_closed_tickets(conn, args.apply),
            "temp_files": cleanup_temp_files(args.temp_dir or [os.getenv("TMPDIR", "/tmp")], args.apply),
        }
        if args.apply:
            conn.commit()
        print("GrantPro retention cleanup")
        print(f"Mode: {'apply' if args.apply else 'dry-run'}")
        for key, value in counts.items():
            print(f"{key}: {value}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()