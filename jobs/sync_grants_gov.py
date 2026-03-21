#!/usr/bin/env python3
"""
Daily Grants.gov Sync Job

Fetches opportunities from the Grants.gov public API and upserts them
into the local grants_catalog table.  Safe to run repeatedly -- uses
INSERT OR REPLACE so duplicates are handled gracefully.

Usage:
    python3 jobs/sync_grants_gov.py                  # default: 500 results
    python3 jobs/sync_grants_gov.py --max-results 100
    python3 jobs/sync_grants_gov.py --keyword energy

Schedule via cron:
    0 4 * * * cd /Users/fbwalker4/.hermes/grant-system && python3 jobs/sync_grants_gov.py >> tracking/sync.log 2>&1
"""

import argparse
import json
import logging
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "tracking" / "grants.db"
LOG_DIR = PROJECT_ROOT / "tracking"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "sync.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("sync_grants_gov")

# ---------------------------------------------------------------------------
# Agency-code -> template mapping (mirrors GrantResearcher._map_agency_to_template)
# ---------------------------------------------------------------------------
AGENCY_TEMPLATE_MAP = {
    "NSF": "nsf",
    "DOE": "doe",
    "NIH": "nih",
    "USDA": "usda",
    "EPA": "epa",
    "DOT": "dot",
    "NIST": "nist",
    "HHS": "hhs",
    "DOD": "dod",
    "NASA": "generic",
    "DHS": "generic",
    "EDA": "generic",
    "NEA": "nea",
    "SBA": "small_business_grant",
}

API_URL = "https://api.grants.gov/v1/api/search"
PAGE_SIZE = 25  # Grants.gov default page size


def _parse_amount(val):
    """Coerce an amount value (string, int, float, None) to int."""
    if val is None:
        return 0
    try:
        return int(float(str(val).replace("$", "").replace(",", "")))
    except (ValueError, TypeError):
        return 0


def fetch_page(keyword=None, page=1, page_size=PAGE_SIZE):
    """Fetch one page of results from the Grants.gov search API."""
    payload = {
        "keyword": keyword or "",
        "oppNum": "",
        "cfda": "",
        "oppStatuses": "forecasted|posted",
        "sortBy": "openDate|desc",
        "rows": page_size,
        "offset": (page - 1) * page_size,
    }
    resp = requests.post(API_URL, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def map_opportunity(opp):
    """Convert a Grants.gov opportunity dict to our grants_catalog schema."""
    agency_code = opp.get("agencyCode") or opp.get("agency", "")
    now = datetime.now().isoformat()

    return {
        "id": str(opp.get("id") or opp.get("opportunityId") or opp.get("oppId", "")),
        "opportunity_number": opp.get("number") or opp.get("opportunityNumber", ""),
        "title": opp.get("title", "Untitled"),
        "agency": opp.get("agencyName") or opp.get("agency", ""),
        "agency_code": agency_code,
        "cfda": opp.get("cfdaNumber") or "",
        "category": opp.get("opportunityCategory") or opp.get("category", ""),
        "amount_min": _parse_amount(opp.get("awardFloor") or opp.get("minAmount")),
        "amount_max": _parse_amount(opp.get("awardCeiling") or opp.get("maxAmount")),
        "open_date": opp.get("openDate") or opp.get("postDate", ""),
        "close_date": opp.get("closeDate") or opp.get("archiveDate", ""),
        "description": opp.get("synopsis") or opp.get("description", ""),
        "eligibility": opp.get("applicantEligibility") or opp.get("eligibility", ""),
        "url": f"https://www.grants.gov/search-results-detail/{opp.get('id') or opp.get('opportunityId', '')}",
        "template": AGENCY_TEMPLATE_MAP.get(agency_code, "generic"),
        "source": "grants_gov",
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }


def upsert_grants(grants):
    """INSERT OR REPLACE a list of mapped grant dicts into grants_catalog."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    for g in grants:
        c.execute(
            """INSERT OR REPLACE INTO grants_catalog
               (id, opportunity_number, title, agency, agency_code, cfda, category,
                amount_min, amount_max, open_date, close_date, description, eligibility,
                url, template, source, status, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                g["id"], g["opportunity_number"], g["title"], g["agency"],
                g["agency_code"], g["cfda"], g["category"],
                g["amount_min"], g["amount_max"], g["open_date"], g["close_date"],
                g["description"], g["eligibility"], g["url"], g["template"],
                g["source"], g["status"], g["created_at"], g["updated_at"],
            ),
        )

    conn.commit()
    conn.close()
    return len(grants)


def archive_expired():
    """Mark grants whose close_date has passed as 'archived',
    unless they are referenced by an active user grant application."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(
        """UPDATE grants_catalog
           SET status = 'archived', updated_at = ?
           WHERE close_date < date('now')
             AND close_date != ''
             AND status = 'active'
             AND id NOT IN (
                 SELECT grant_id FROM user_applications
                 WHERE status IN ('draft','in_progress','submitted','intake','drafting','review')
                   AND grant_id IS NOT NULL
             )""",
        (datetime.now().isoformat(),),
    )
    archived = c.rowcount
    conn.commit()
    conn.close()
    return archived


def run_sync(keyword=None, max_results=500):
    """Main sync entry point."""
    logger.info("=== Grants.gov Sync Started ===")

    # Ensure DB and table exist
    sys.path.insert(0, str(PROJECT_ROOT / "core"))
    from grant_db import init_db, seed_grants_catalog
    init_db()
    seed_grants_catalog()

    total_fetched = 0
    page = 1
    all_grants = []

    while total_fetched < max_results:
        try:
            data = fetch_page(keyword=keyword, page=page, page_size=PAGE_SIZE)
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed on page {page}: {e}")
            break

        # The API response structure may vary; try common keys
        hits = (
            data.get("oppHits", [])
            or data.get("opportunities", [])
            or data.get("oppHits", {}).get("hit", [])
        )
        if isinstance(hits, dict):
            hits = hits.get("hit", [])

        if not hits:
            logger.info(f"No more results at page {page}")
            break

        mapped = [map_opportunity(opp) for opp in hits]
        all_grants.extend(mapped)
        total_fetched += len(hits)
        page += 1

        # Rate-limit courtesy: 1 second between pages
        time.sleep(1)

        if len(hits) < PAGE_SIZE:
            break  # Last page

    if all_grants:
        inserted = upsert_grants(all_grants)
        logger.info(f"Upserted {inserted} grants from Grants.gov")
    else:
        logger.info("No new grants fetched from API")

    archived = archive_expired()
    logger.info(f"Archived {archived} expired grants")

    # Final count
    conn = sqlite3.connect(str(DB_PATH))
    total = conn.execute(
        "SELECT COUNT(*) FROM grants_catalog WHERE status = 'active'"
    ).fetchone()[0]
    conn.close()
    logger.info(f"Total active grants in catalog: {total}")
    logger.info("=== Grants.gov Sync Complete ===")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync grants from Grants.gov API")
    parser.add_argument("--keyword", default=None, help="Search keyword (optional)")
    parser.add_argument("--max-results", type=int, default=500, help="Max results to fetch")
    args = parser.parse_args()
    run_sync(keyword=args.keyword, max_results=args.max_results)
