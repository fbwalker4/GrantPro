#!/usr/bin/env python3
"""
Award Winner Detection Job
Queries USAspending.gov for recent federal award data and cross-references
recipients against GrantPro clients and users. On match, creates an
award_matches record and sends a congratulations email with a link to
the testimonial form.

Usage:
    python3 jobs/check_awards.py
"""

import json
import logging
import secrets
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Paths & logging
# ---------------------------------------------------------------------------
GRANT_SYSTEM = Path.home() / ".hermes" / "grant-system"
DB_PATH = GRANT_SYSTEM / "tracking" / "grants.db"
LOG_DIR = GRANT_SYSTEM / "tracking"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "check_awards.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("check_awards")

# Add core/ to sys.path so we can import email_system
sys.path.insert(0, str(GRANT_SYSTEM / "core"))

BASE_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
PORTAL_BASE = "http://localhost:5001"

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    """Return a connection with Row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_org_names():
    """Collect all distinct organization names from clients and users tables."""
    conn = get_db()
    orgs = set()

    # From clients table
    try:
        rows = conn.execute(
            "SELECT DISTINCT organization_name FROM clients WHERE organization_name IS NOT NULL AND organization_name != ''"
        ).fetchall()
        for r in rows:
            orgs.add(r["organization_name"])
    except Exception as e:
        logger.warning(f"Could not read clients table: {e}")

    # From users table
    try:
        rows = conn.execute(
            "SELECT DISTINCT organization_name FROM users WHERE organization_name IS NOT NULL AND organization_name != ''"
        ).fetchall()
        for r in rows:
            orgs.add(r["organization_name"])
    except Exception as e:
        logger.warning(f"Could not read users table: {e}")

    conn.close()
    return orgs


def find_matching_user(org_name):
    """Find the first user whose organization_name matches (LIKE) the given org_name.
    Returns a dict with user_id, email, organization_name or None."""
    conn = get_db()

    # Try users table first (portal users)
    try:
        row = conn.execute(
            "SELECT id, email, organization_name FROM users WHERE organization_name LIKE ? LIMIT 1",
            (f"%{org_name}%",),
        ).fetchone()
        if row:
            conn.close()
            return dict(row)
    except Exception:
        pass

    # Fall back to clients table
    try:
        row = conn.execute(
            "SELECT id, contact_email AS email, organization_name FROM clients WHERE organization_name LIKE ? LIMIT 1",
            (f"%{org_name}%",),
        ).fetchone()
        if row:
            conn.close()
            return dict(row)
    except Exception:
        pass

    conn.close()
    return None


def award_already_recorded(recipient_name, award_amount, award_date):
    """Check if we have already recorded this award to avoid duplicates."""
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM award_matches WHERE grant_name = ? AND award_amount = ? AND award_date = ?",
        (recipient_name, award_amount, award_date),
    ).fetchone()
    conn.close()
    return row is not None


def create_award_match(user_id, grant_name, award_amount, award_date, source):
    """Insert a new award_matches record and return the record dict."""
    conn = get_db()
    match_id = f"award-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(4)}"
    token = secrets.token_urlsafe(32)
    now = datetime.now().isoformat()

    conn.execute(
        """INSERT INTO award_matches
           (id, user_id, grant_id, grant_name, award_amount, award_date, source, notified, testimonial_token, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
        (match_id, user_id, None, grant_name, award_amount, award_date, source, token, now),
    )
    conn.commit()
    conn.close()

    return {
        "id": match_id,
        "user_id": user_id,
        "grant_name": grant_name,
        "award_amount": award_amount,
        "award_date": award_date,
        "testimonial_token": token,
    }


def mark_notified(match_id):
    """Set notified=1 on an award_matches row."""
    conn = get_db()
    conn.execute("UPDATE award_matches SET notified = 1 WHERE id = ?", (match_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# USAspending.gov API
# ---------------------------------------------------------------------------

def fetch_recent_awards(days_back=30, limit=100):
    """Query USAspending.gov for awards in the last `days_back` days."""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    payload = {
        "filters": {
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            "award_type_codes": ["02", "03", "04", "05"],  # Grants
        },
        "fields": [
            "Award ID",
            "Recipient Name",
            "Award Amount",
            "Start Date",
            "Awarding Agency",
            "Award Type",
        ],
        "limit": limit,
        "page": 1,
        "sort": "Award Amount",
        "order": "desc",
    }

    try:
        resp = requests.post(BASE_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        logger.info(f"Fetched {len(results)} awards from USAspending.gov ({start_date} to {end_date})")
        return results
    except requests.RequestException as e:
        logger.error(f"USAspending API error: {e}")
        return []


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def check_awards():
    """Main entry point: fetch awards, match against our orgs, notify."""
    logger.info("Starting award check run")

    # Ensure DB tables exist
    sys.path.insert(0, str(GRANT_SYSTEM / "core"))
    from grant_db import init_db
    init_db()

    org_names = get_org_names()
    if not org_names:
        logger.info("No organization names found in database — nothing to match")
        return

    logger.info(f"Loaded {len(org_names)} organization names to match against")

    awards = fetch_recent_awards()
    if not awards:
        logger.info("No awards returned from API")
        return

    matches_found = 0

    for award in awards:
        recipient = award.get("Recipient Name") or ""
        amount = award.get("Award Amount") or 0
        award_date = award.get("Start Date") or ""
        agency = award.get("Awarding Agency") or ""
        grant_name = f"{agency} Award" if agency else "Federal Award"

        # Cross-reference recipient against our org names using LIKE matching
        for org in org_names:
            # Case-insensitive substring match in both directions
            if org.lower() in recipient.lower() or recipient.lower() in org.lower():
                # Check for duplicate
                if award_already_recorded(grant_name, amount, award_date):
                    logger.debug(f"Already recorded: {recipient} - ${amount:,.2f}")
                    continue

                user = find_matching_user(org)
                if not user:
                    continue

                logger.info(f"MATCH: {recipient} <-> {org} | ${amount:,.2f} | {grant_name}")

                match = create_award_match(
                    user_id=user["id"],
                    grant_name=grant_name,
                    award_amount=amount,
                    award_date=award_date,
                    source="usaspending.gov",
                )

                # Send congratulations email
                testimonial_url = f"{PORTAL_BASE}/testimonial/{match['testimonial_token']}"
                email = user.get("email", "")

                if email:
                    try:
                        from email_system import send_award_congratulations
                        result = send_award_congratulations(
                            email=email,
                            grant_name=grant_name,
                            org_name=org,
                            testimonial_url=testimonial_url,
                        )
                        logger.info(f"Email sent to {email}: {result}")
                        mark_notified(match["id"])
                    except Exception as e:
                        logger.error(f"Failed to send email to {email}: {e}")
                        # Log to console as fallback
                        print(f"[AWARD MATCH] {org} — {grant_name} — ${amount:,.2f}")
                        print(f"[TESTIMONIAL] {testimonial_url}")
                else:
                    logger.warning(f"No email for user {user['id']}; logging match only")
                    print(f"[AWARD MATCH] {org} — {grant_name} — ${amount:,.2f}")
                    print(f"[TESTIMONIAL] {testimonial_url}")

                matches_found += 1
                break  # One match per award is enough

    logger.info(f"Award check complete: {matches_found} new matches from {len(awards)} awards")


if __name__ == "__main__":
    check_awards()
