#!/usr/bin/env python3
"""
GrantPro Database Seeder
Populates grants_catalog in Supabase from grants.gov (using apply07 endpoint)

Uses grant_key (opp_num::status) as the dedup target since that is now the
primary key. This allows the same grant to exist in multiple statuses
(posted, forecasted, closed) as separate rows.
"""
import os
import sys
import json
import urllib.parse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load .env
env_path = os.path.join(SCRIPT_DIR, '..', '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, _, v = line.partition('=')
                os.environ[k.strip()] = v.strip()

SUPABASE_URL = os.environ.get("GP_SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("GP_SUPABASE_KEY", "")
GRANTS_GOV_API = "https://apply07.grants.gov/grantsws/rest/opportunities/search"

DB_URL = os.environ.get("DATABASE_URL", "")


def get_db_conn():
    """Get a psycopg2 connection to Supabase."""
    if not DB_URL:
        raise ValueError("DATABASE_URL not set")
    p = urllib.parse.urlparse(DB_URL)
    pw = urllib.parse.unquote(p.password) if '%' in p.password else p.password
    import psycopg2
    return psycopg2.connect(
        host=p.hostname, port=p.port or 5432, dbname=p.path[1:],
        user=p.username, password=pw
    )


def fetch_grants_curl(keyword, statuses='forecasted|posted', rows=500, offset=0):
    """Fetch grants from Grants.gov using curl (bypasses Python DNS issues)."""
    import subprocess
    payload = json.dumps({
        "keyword": keyword, "oppNum": "", "cfda": "",
        "oppStatuses": statuses, "sortBy": "openDate|desc",
        "rows": rows, "offset": offset
    })
    r = subprocess.run([
        'curl', '-s', '--max-time', '30', '-X', 'POST',
        'https://apply07.grants.gov/grantsws/rest/opportunities/search',
        '-H', 'Content-Type: application/json',
        '-H', 'User-Agent: GrantPro/1.0',
        '-d', payload
    ], capture_output=True, text=True)
    try:
        return json.loads(r.stdout).get('oppHits', [])
    except Exception:
        return []


def parse_grant(hit):
    """Parse a grants.gov hit into a grant dict."""
    opp_id = str(hit.get('id', ''))
    opp_num = str(hit.get('number', opp_id))
    status = str(hit.get('oppStatus', 'posted'))
    return {
        'id': opp_id,
        'opportunity_number': opp_num,
        'title': str(hit.get('title', 'Untitled'))[:500],
        'agency': str(hit.get('agency', '')),
        'agency_code': str(hit.get('agencyCode', '')),
        'cfda': str(hit.get('cfdaList', '')),
        'category': '',
        'amount_min': 0,
        'amount_max': 0,
        'open_date': str(hit.get('openDate', '')),
        'close_date': str(hit.get('closeDate', '')),
        'description': '',
        'eligibility': str(hit.get('eligibility', '')),
        'url': f"https://grants.gov/content/go/funding-opportunity-details?docId={opp_id}&collectionId=&isRandom=false",
        'source': 'grants.gov',
        'status': status,
        'grant_type': str(hit.get('fundingInstrumentType', '')),
        'direct_apply': False,
        'ineligible_message': '',
        'grant_key': f"{opp_num}::{status}"  # Unique dedup key: opp_num + status
    }


def upsert_grants_batch(conn, grants):
    """Bulk upsert grants using grant_key as the conflict target (now the PK)."""
    if not grants:
        return 0
    c = conn.cursor()
    BATCH = 100
    total = 0
    for i in range(0, len(grants), BATCH):
        batch = grants[i:i+BATCH]
        values = []
        for g in batch:
            values.append((
                g['id'], g['opportunity_number'], g['title'], g['agency'],
                g['agency_code'], g['cfda'], g['open_date'], g['close_date'],
                g['eligibility'], g['url'], g['source'], g['status'],
                g['grant_type'], g['direct_apply'], g['grant_key'],
                g['ineligible_message'], g['category'], g['amount_min'],
                g['amount_max'], g['description']
            ))
        sql = """
            INSERT INTO grants_catalog (
                id, opportunity_number, title, agency, agency_code, cfda,
                open_date, close_date, eligibility, url, source, status,
                grant_type, direct_apply, grant_key, ineligible_message,
                category, amount_min, amount_max, description
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (grant_key) DO UPDATE SET
                title = EXCLUDED.title,
                agency = EXCLUDED.agency,
                close_date = EXCLUDED.close_date,
                status = EXCLUDED.status,
                updated_at = now()
        """
        try:
            c.executemany(sql, values)
            conn.commit()
            total += len(batch)
        except Exception as e:
            print(f"    Batch error: {e}")
    c.close()
    return total


def main():
    KEYWORDS = [
        "housing", "community development", "HUD", "urban development",
        "homeless", "infrastructure", "public housing", "CDBG",
        "emergency solution", "housing counseling", "lead hazard",
        "energy efficiency", "weatherization", "rural housing",
        "tribal housing", "native american housing", "section 8",
        "public facility", "water sewer", "economic development",
        "urban planning", "zoning", "land use", "redevelopment",
        "disaster recovery", "community housing", "rental assistance",
        "affordable housing", "fair housing", "housing authority",
        "homeless assistance", "transitional housing", "rapid rehousing",
        "youth housing", "senior housing", "housing construction",
        "homeownership", "housing finance", "mortgage assistance",
        "housing development", "neighborhood revitalization"
    ]

    print("GrantPro Database Seeder")
    print(f"Supabase: {SUPABASE_URL}")
    print(f"Keywords: {len(KEYWORDS)}")
    print("---")

    conn = get_db_conn()

    # Deduplicate by grant_key across all keywords
    seen = {}  # grant_key -> True
    total_inserted = 0

    # Phase 1: posted + forecasted
    for kw in KEYWORDS:
        hits = fetch_grants_curl(kw, 'forecasted|posted', 500)
        print(f"[{kw}]: {len(hits)} hits", end="")

        new_grants = []
        for hit in hits:
            g = parse_grant(hit)
            key = g['grant_key']
            if key and key not in seen:
                seen[key] = True
                new_grants.append(g)

        if new_grants:
            n = upsert_grants_batch(conn, new_grants)
            total_inserted += n
            print(f" → {n} new")
        else:
            print(" → 0 new")

        import time; time.sleep(0.3)

    # Phase 2: closed grants (subset of keywords, smaller page)
    CLOSED_KEYWORDS = ["housing", "community development", "public housing",
                       "affordable housing", "homeless"]
    print("\n--- Closed grants ---")
    for kw in CLOSED_KEYWORDS:
        hits = fetch_grants_curl(kw, 'closed', 100)
        print(f"[{kw}/closed]: {len(hits)} hits", end="")

        new_grants = []
        for hit in hits:
            g = parse_grant(hit)
            key = g['grant_key']
            if key and key not in seen:
                seen[key] = True
                new_grants.append(g)

        if new_grants:
            n = upsert_grants_batch(conn, new_grants)
            total_inserted += n
            print(f" → {n} new")
        else:
            print(" → 0 new")

        import time; time.sleep(0.3)

    conn.close()
    print(f"\n✅ Done: {len(seen)} unique grants, {total_inserted} total inserted")


if __name__ == "__main__":
    main()
