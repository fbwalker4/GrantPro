#!/usr/bin/env python3
"""
GrantPro Database Seeder
Populates grants_catalog in Supabase from grants.gov (using apply07 endpoint)
"""
import os
import sys
import requests
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load .env
env_path = os.path.join(SCRIPT_DIR, '..', '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                os.environ[k] = v

SUPABASE_URL = os.environ.get("GP_SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("GP_SUPABASE_KEY", "")

GRANTS_GOV_API = "https://apply07.grants.gov/grantsws/rest/opportunities/search"

def fetch_grants(keyword, rows=1000, offset=0):
    payload = {
        "keyword": keyword,
        "oppNum": "",
        "cfda": "",
        "oppStatuses": "forecasted|posted|closed",
        "sortBy": "openDate|desc",
        "rows": rows,
        "offset": offset
    }
    resp = requests.post(GRANTS_GOV_API, json=payload, headers={
        "Content-Type": "application/json",
        "User-Agent": "GrantPro/1.0"
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    hits = data.get("oppHits", [])
    total = data.get("hitCount", 0)
    return hits, total

def parse_grant(hit):
    opp_id = str(hit.get("id", ""))
    return {
        "id": opp_id,
        "opportunity_number": str(hit.get("number", opp_id)),
        "title": str(hit.get("title", "Untitled"))[:500],
        "agency": str(hit.get("agency", "")),
        "agency_code": str(hit.get("agencyCode", "")),
        "cfda": str(hit.get("cfdaList", "")),
        "category": "",
        "amount_min": 0,
        "amount_max": 0,
        "open_date": str(hit.get("openDate", "")),
        "close_date": str(hit.get("closeDate", "")),
        "description": "",
        "eligibility": str(hit.get("eligibility", "")),
        "url": f"https://grants.gov/content/go/funding-opportunity-details?docId={opp_id}&collectionId=&isRandom=false",
        "source": "grants.gov",
        "status": str(hit.get("oppStatus", "posted")),
        "grant_type": str(hit.get("fundingInstrumentType", "")),
        "direct_apply": False,
        "ineligible_message": ""
    }

def upsert_grants(grants):
    if not grants:
        return 0
    url = f"{SUPABASE_URL}/rest/v1/grants_catalog"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    resp = requests.post(url, json=grants, headers=headers, timeout=60)
    if resp.status_code not in (200, 201):
        print(f"  Supabase error {resp.status_code}: {resp.text[:200]}")
        return 0
    return len(grants)

def main():
    keywords = [
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

    print(f"GrantPro Database Seeder")
    print(f"Supabase: {SUPABASE_URL}")
    print(f"Keywords: {len(keywords)}")
    print("---")

    seen = {}
    total_inserted = 0

    for kw in keywords:
        hits, hit_count = fetch_grants(kw)
        print(f"'{kw}': {hit_count} total, {len(hits)} fetched", end="")

        new_grants = []
        for hit in hits:
            opp_id = str(hit.get("id", ""))
            if opp_id and opp_id not in seen:
                seen[opp_id] = True
                new_grants.append(parse_grant(hit))

        if new_grants:
            inserted = upsert_grants(new_grants)
            total_inserted += inserted
            print(f" → {inserted} new grants")
        else:
            print(" → 0 new")

        print(f"  Running total unique: {len(seen)}")

    print(f"\n✅ Done: {len(seen)} unique grants seeded")

if __name__ == "__main__":
    main()
