#!/usr/bin/env python3
"""
Winning Grants Library -- collect and search successful federal grant awards.

Data source: USAspending.gov API (no auth required).
Storage: local DB via db_connection.get_connection().
"""

import re
import time
import uuid
import logging
from datetime import datetime, timedelta

import requests

from db_connection import get_connection

logger = logging.getLogger(__name__)

BASE_URL = "https://api.usaspending.gov"

# Grant type codes (Non-Loan Assistance)
GRANT_TYPE_CODES = ["02", "03", "04", "05"]

GRANT_FIELDS = [
    "Award ID",
    "Recipient Name",
    "Recipient UEI",
    "Award Amount",
    "Total Outlays",
    "Description",
    "Start Date",
    "End Date",
    "Awarding Agency",
    "Awarding Sub Agency",
    "CFDA Number",
    "Place of Performance State Code",
    "Place of Performance City Code",
    "Award Type",
    "generated_internal_id",
]

# ------------------------------------------------------------------
# Table bootstrap
# ------------------------------------------------------------------

def init_awards_table():
    """Create the successful_awards table if it does not exist."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS successful_awards (
                id TEXT PRIMARY KEY,
                usaspending_award_id TEXT UNIQUE,
                recipient_name TEXT,
                recipient_state TEXT,
                recipient_city TEXT,
                recipient_uei TEXT,
                award_amount DOUBLE PRECISION,
                total_outlays DOUBLE PRECISION,
                agency TEXT,
                sub_agency TEXT,
                cfda_number TEXT,
                cfda_title TEXT,
                cfda_objectives TEXT,
                award_description TEXT,
                funding_opportunity_number TEXT,
                start_date TEXT,
                end_date TEXT,
                award_type TEXT,
                keywords TEXT,
                created_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_awards_agency ON successful_awards(agency)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_awards_state ON successful_awards(recipient_state)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_awards_cfda ON successful_awards(cfda_number)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_awards_amount ON successful_awards(award_amount)")
        conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------------
# USAspending API helpers
# ------------------------------------------------------------------

def _build_filters(agency=None, state=None, cfda=None, min_amount=10000, years_back=3):
    """Build the AdvancedFilterObject for the USAspending search endpoint."""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")

    filters = {
        "award_type_codes": GRANT_TYPE_CODES,
        "time_period": [{"start_date": start_date, "end_date": end_date}],
        "award_amounts": [{"lower_bound": min_amount}],
    }
    if agency:
        filters["agencies"] = [
            {"type": "awarding", "tier": "toptier", "name": agency}
        ]
    if state:
        filters["place_of_performance_locations"] = [
            {"country": "USA", "state": state}
        ]
    if cfda:
        filters["program_numbers"] = [cfda] if isinstance(cfda, str) else cfda
    return filters


def _fetch_page(filters, page=1, limit=100):
    """Fetch one page of results from spending_by_award."""
    url = f"{BASE_URL}/api/v2/search/spending_by_award/"
    payload = {
        "filters": filters,
        "fields": GRANT_FIELDS,
        "limit": limit,
        "page": page,
        "sort": "Award Amount",
        "order": "desc",
        "subawards": False,
    }
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def _fetch_award_detail(internal_id):
    """Fetch full detail for a single award (CFDA objectives, funding opp, etc.)."""
    url = f"{BASE_URL}/api/v2/awards/{internal_id}/"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------------
# collect_awards -- fetch from API and store locally
# ------------------------------------------------------------------

def collect_awards(agency=None, state=None, cfda=None, min_amount=10000,
                   years_back=3, limit=500, enrich_details=True, enrich_max=50):
    """
    Fetch grant awards from USAspending.gov API and store in DB.

    Returns the number of new rows inserted.
    """
    init_awards_table()

    filters = _build_filters(agency=agency, state=state, cfda=cfda,
                             min_amount=min_amount, years_back=years_back)

    all_results = []
    per_page = min(limit, 100)
    max_pages = (limit // per_page) + 1

    for page_num in range(1, max_pages + 1):
        logger.info("Fetching page %d for agency=%s state=%s ...", page_num, agency, state)
        data = _fetch_page(filters, page=page_num, limit=per_page)
        results = data.get("results", [])
        if not results:
            break
        all_results.extend(results)
        if len(all_results) >= limit:
            all_results = all_results[:limit]
            break
        has_next = data.get("page_metadata", {}).get("hasNext", False)
        if not has_next:
            break
        time.sleep(0.5)

    # Optionally enrich top awards with CFDA objectives and funding opp number
    detail_cache = {}
    if enrich_details:
        for i, award in enumerate(all_results[:enrich_max]):
            internal_id = award.get("generated_internal_id")
            if not internal_id:
                continue
            try:
                detail = _fetch_award_detail(internal_id)
                detail_cache[internal_id] = detail
            except Exception as exc:
                logger.warning("Could not enrich award %s: %s", internal_id, exc)
            time.sleep(0.4)

    # Store in DB
    conn = get_connection()
    inserted = 0
    try:
        for award in all_results:
            internal_id = award.get("generated_internal_id", "")
            award_id = award.get("Award ID", internal_id)

            # Pull enriched data if available
            detail = detail_cache.get(internal_id, {})
            cfda_info = (detail.get("cfda_info") or [{}])[0] if detail else {}
            funding_opp = detail.get("funding_opportunity") or {}
            recipient_detail = (detail.get("recipient") or {}).get("location", {}) if detail else {}

            row_id = str(uuid.uuid4())
            try:
                conn.execute("""
                    INSERT INTO successful_awards
                        (id, usaspending_award_id, recipient_name, recipient_state,
                         recipient_city, recipient_uei, award_amount, total_outlays,
                         agency, sub_agency, cfda_number, cfda_title, cfda_objectives,
                         award_description, funding_opportunity_number, start_date,
                         end_date, award_type, keywords, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (usaspending_award_id) DO NOTHING
                """, (
                    row_id,
                    award_id,
                    award.get("Recipient Name", ""),
                    award.get("Place of Performance State Code", "") or recipient_detail.get("state_code", ""),
                    recipient_detail.get("city_name", "") or str(award.get("Place of Performance City Code", "")),
                    award.get("Recipient UEI", ""),
                    award.get("Award Amount"),
                    award.get("Total Outlays"),
                    award.get("Awarding Agency", ""),
                    award.get("Awarding Sub Agency", ""),
                    award.get("CFDA Number", "") or cfda_info.get("cfda_number", ""),
                    cfda_info.get("cfda_title", ""),
                    cfda_info.get("cfda_objectives", ""),
                    award.get("Description", "") or detail.get("description", ""),
                    funding_opp.get("number", ""),
                    award.get("Start Date", ""),
                    award.get("End Date", ""),
                    award.get("Award Type", ""),
                    "",  # keywords populated later if needed
                    datetime.now().isoformat(),
                ))
                inserted += 1
            except Exception as exc:
                # Duplicate or other constraint -- skip
                logger.debug("Skipped award %s: %s", award_id, exc)

        conn.commit()
    finally:
        conn.close()

    logger.info("Collected %d awards, inserted %d new rows (agency=%s, state=%s)",
                len(all_results), inserted, agency, state)
    return inserted


# ------------------------------------------------------------------
# search_awards -- query local DB
# ------------------------------------------------------------------

def search_awards(query=None, agency=None, state=None, min_amount=None,
                  max_amount=None, limit=20, offset=0):
    """
    Search the local awards database. Returns list of award dicts.
    Text search matches against award_description, cfda_title, cfda_objectives,
    and recipient_name.
    """
    init_awards_table()

    conditions = []
    params = []

    if query and query.strip():
        terms = query.strip().split()
        for term in terms:
            like = f"%{term}%"
            conditions.append(
                "(award_description LIKE ? OR cfda_title LIKE ? OR cfda_objectives LIKE ? OR recipient_name LIKE ?)"
            )
            params.extend([like, like, like, like])

    if agency and agency.strip():
        conditions.append("agency LIKE ?")
        params.append(f"%{agency.strip()}%")

    if state and state.strip():
        conditions.append("recipient_state = ?")
        params.append(state.strip().upper())

    if min_amount is not None:
        conditions.append("award_amount >= ?")
        params.append(float(min_amount))

    if max_amount is not None:
        conditions.append("award_amount <= ?")
        params.append(float(max_amount))

    where = " AND ".join(conditions) if conditions else "1=1"

    sql = f"""
        SELECT * FROM successful_awards
        WHERE {where}
        ORDER BY award_amount DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    conn = get_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ------------------------------------------------------------------
# get_similar_awards -- keyword matching for project descriptions
# ------------------------------------------------------------------

def _extract_keywords(text, min_length=4):
    """Extract meaningful keywords from text, filtering out common stopwords."""
    stopwords = {
        "the", "and", "for", "that", "this", "with", "from", "will", "have",
        "been", "are", "was", "were", "being", "their", "they", "which",
        "would", "could", "should", "about", "into", "through", "during",
        "before", "after", "above", "below", "between", "each", "other",
        "some", "such", "than", "more", "also", "just", "only", "very",
        "program", "project", "grant", "funding", "funds", "federal",
        "provide", "support", "assist", "include", "including",
    }
    words = re.findall(r'[a-zA-Z]+', text.lower())
    return list(set(w for w in words if len(w) >= min_length and w not in stopwords))


def get_similar_awards(project_description, agency=None, state=None, limit=5):
    """
    Find awards similar to a project description using keyword matching.
    Returns ranked results.
    """
    init_awards_table()
    keywords = _extract_keywords(project_description)
    if not keywords:
        return []

    # Build OR conditions for each keyword across description fields
    keyword_conditions = []
    params = []
    for kw in keywords[:10]:  # cap at 10 keywords to keep query reasonable
        like = f"%{kw}%"
        keyword_conditions.append(
            "(award_description LIKE ? OR cfda_title LIKE ? OR cfda_objectives LIKE ?)"
        )
        params.extend([like, like, like])

    keyword_where = " OR ".join(keyword_conditions)

    extra_conditions = []
    if agency and agency.strip():
        extra_conditions.append("agency LIKE ?")
        params.append(f"%{agency.strip()}%")
    if state and state.strip():
        extra_conditions.append("recipient_state = ?")
        params.append(state.strip().upper())

    where_parts = [f"({keyword_where})"]
    where_parts.extend(extra_conditions)
    where_clause = " AND ".join(where_parts)

    sql = f"""
        SELECT * FROM successful_awards
        WHERE {where_clause}
        ORDER BY award_amount DESC
        LIMIT ?
    """
    params.append(limit)

    conn = get_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
        results = [dict(r) for r in rows]
    finally:
        conn.close()

    # Score results by number of keyword matches
    scored = []
    for r in results:
        text = " ".join([
            r.get("award_description") or "",
            r.get("cfda_title") or "",
            r.get("cfda_objectives") or "",
        ]).lower()
        score = sum(1 for kw in keywords if kw in text)
        scored.append((score, r))

    scored.sort(key=lambda x: (-x[0], -(x[1].get("award_amount") or 0)))
    return [r for _, r in scored[:limit]]


# ------------------------------------------------------------------
# get_award_detail
# ------------------------------------------------------------------

def get_award_detail(award_id):
    """Get full details of a single award from local DB."""
    init_awards_table()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM successful_awards WHERE id = ?", (award_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ------------------------------------------------------------------
# get_awards_stats
# ------------------------------------------------------------------

def get_awards_stats():
    """Return stats: total awards, by agency, by state, amount range."""
    init_awards_table()
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) as cnt FROM successful_awards").fetchone()
        total_count = total["cnt"] if total else 0

        amount_stats = conn.execute("""
            SELECT
                COALESCE(SUM(award_amount), 0) as total_amount,
                COALESCE(AVG(award_amount), 0) as avg_amount,
                COALESCE(MIN(award_amount), 0) as min_amount,
                COALESCE(MAX(award_amount), 0) as max_amount
            FROM successful_awards
        """).fetchone()

        by_agency = conn.execute("""
            SELECT agency, COUNT(*) as cnt, COALESCE(SUM(award_amount), 0) as total
            FROM successful_awards
            WHERE agency IS NOT NULL AND agency != ''
            GROUP BY agency
            ORDER BY cnt DESC
            LIMIT 20
        """).fetchall()

        by_state = conn.execute("""
            SELECT recipient_state, COUNT(*) as cnt, COALESCE(SUM(award_amount), 0) as total
            FROM successful_awards
            WHERE recipient_state IS NOT NULL AND recipient_state != ''
            GROUP BY recipient_state
            ORDER BY cnt DESC
            LIMIT 20
        """).fetchall()

        return {
            "total_awards": total_count,
            "total_amount": amount_stats["total_amount"] if amount_stats else 0,
            "avg_amount": amount_stats["avg_amount"] if amount_stats else 0,
            "min_amount": amount_stats["min_amount"] if amount_stats else 0,
            "max_amount": amount_stats["max_amount"] if amount_stats else 0,
            "by_agency": [dict(r) for r in by_agency],
            "by_state": [dict(r) for r in by_state],
        }
    finally:
        conn.close()
