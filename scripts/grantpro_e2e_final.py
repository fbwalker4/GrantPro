#!/usr/bin/env python3
"""
GrantPro Full E2E — Corrected with real generic template sections.
"""
import requests, re, sys, time, psycopg2, urllib.parse

BASE_URL = "https://grantpro.org"
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (GrantPro E2E Bot)'})

GRANT_APP_ID = "grant-20260410-013501-c4be33e4"

# Generic template sections (what FHLB AHP actually uses)
SECTIONS = [
    ('project_summary', 'Project Summary/Abstract'),
    ('project_description', 'Project Description'),
    ('budget', 'Budget'),
    ('budget_justification', 'Budget Justification'),
    ('biographical', 'Key Personnel'),
    ('facilities', 'Facilities and Resources'),
]

def get_csrf(html):
    m = re.search(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', html)
    return m.group(1) if m else ""

def do_login():
    r = session.get(f"{BASE_URL}/login", timeout=30)
    resp = session.post(f"{BASE_URL}/login", data={
        'email': 'qa_paid_coastalhousing@test.com',
        'password': 'GrantPro2026!',
        'csrf_token': get_csrf(r.text)
    }, timeout=30, allow_redirects=True)
    return 'dashboard' in resp.url.lower()

def generate_section(grant_id, section):
    r = session.get(f"{BASE_URL}/grant/{grant_id}/checklist", timeout=30)
    csrf = get_csrf(r.text)
    resp = session.post(
        f"{BASE_URL}/grant/{grant_id}/generate/{section}",
        data={'csrf_token': csrf, 'section': section},
        timeout=90,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-Actor': 'XMLHttpRequest',
            'Referer': f"{BASE_URL}/grant/{grant_id}/checklist"
        }
    )
    try:
        data = resp.json()
        if data.get('error'):
            return False, data['error']
        return True, f"{len(data.get('content','')):,} chars"
    except:
        return False, f"HTTP {resp.status_code}"

def download(grant_id, fmt):
    r = session.get(f"{BASE_URL}/grant/{grant_id}/download/{fmt}", timeout=60)
    if r.status_code == 200 and len(r.content) > 500:
        with open(f'/tmp/grantpro_e2e.{fmt}', 'wb') as f:
            f.write(r.content)
        return True, f"{len(r.content):,} bytes"
    return False, f"HTTP {r.status_code}, size={len(r.content)}"

def submit(grant_id):
    """Submit with proper non-redirect following to detect 302."""
    r = session.get(f"{BASE_URL}/grant/{grant_id}/mark-submitted", timeout=30)
    csrf = get_csrf(r.text)
    resp = session.post(
        f"{BASE_URL}/grant/{grant_id}/mark-submitted",
        data={
            'csrf_token': csrf,
            'submission_date': '2026-04-09',
            'confirmation_number': 'E2E-COASTAL-FHLB-001',
            'portal_used': 'GrantPro Direct',
            'notes': 'E2E test with all sections AI-generated via GrantPro'
        },
        timeout=30,
        allow_redirects=False
    )
    if resp.status_code == 302:
        loc = resp.headers.get('Location', '')
        return True, f"302 → {loc}"
    if resp.status_code == 200:
        # Check for flash/error in response
        if any(k in resp.text.lower() for k in ['checklist', 'complete', 'cannot submit', 'flash']):
            m = re.search(r'flash[^>]*>([^<]+)', resp.text, re.I)
            return False, f"Gate blocked: {(m.group(1) if m else 'checklist incomplete')[:80]}"
        return False, f"200 with form (no redirect)"
    return False, f"HTTP {resp.status_code}"

def db_status(grant_id):
    pw = urllib.parse.unquote('GrantPro2026%21Secure')
    conn = psycopg2.connect(host='aws-1-us-east-1.pooler.supabase.com', port=6543,
                            dbname='postgres', user='postgres.mubghncbtnkjkywbcfts', password=pw)
    conn.autocommit = True
    c = conn.cursor()
    c.execute("SELECT status, submitted_at, grant_name FROM grants WHERE id = %s", (grant_id,))
    row = c.fetchone()
    conn.close()
    return row

print("=" * 60)
print("GrantPro Full E2E — FHLB AHP Application (Generic Template)")
print("=" * 60)

results = []

# Login
print("\n[1] Login")
ok = do_login()
results.append(("Login", ok))
print(f"    {'✓' if ok else '✗'} Login as Coastal Housing Authority")

# Generate all sections
print(f"\n[2] AI Generate ({len(SECTIONS)} sections)")
for section_id, label in SECTIONS:
    ok, msg = generate_section(GRANT_APP_ID, section_id)
    results.append((f"AI: {label}", ok, msg))
    icon = '✓' if ok else '✗'
    print(f"    {icon} {label}: {msg}")

# Downloads
print(f"\n[3] Document Downloads")
for fmt in ['docx', 'pdf']:
    ok, msg = download(GRANT_APP_ID, fmt)
    results.append((f"{fmt.upper()} Download", ok, msg))
    icon = '✓' if ok else '✗'
    print(f"    {icon} {fmt.upper()}: {msg}")

# Submit
print(f"\n[4] Submit Application")
ok, msg = submit(GRANT_APP_ID)
results.append(("Submit", ok, msg))
icon = '✓' if ok else '✗'
print(f"    {icon} Submit: {msg}")

# DB check
print(f"\n[5] Database Verification")
row = db_status(GRANT_APP_ID)
if row:
    print(f"    Grant: {str(row[2])[:50]}")
    print(f"    Status: {row[0]}, Submitted: {row[1]}")
    db_ok = row[0] == 'submitted'
    results.append(("DB: submitted status", db_ok, f"status={row[0]}, submitted_at={row[1]}"))
    print(f"    {'✓' if db_ok else '✗'} Status = 'submitted'")
else:
    results.append(("DB: record found", False, "NOT FOUND"))
    print(f"    ✗ Grant record not found")

# Summary
print("\n" + "=" * 60)
print("FINAL RESULT")
print("=" * 60)
passed = sum(1 for _, ok, *_ in results if ok)
total = len(results)
failed = total - passed
for name, ok, *rest in results:
    msg = rest[0] if rest else ''
    icon = '✓' if ok else '✗'
    print(f"  {icon} {name}: {str(msg)[:80]}")
print(f"\n  {passed}/{total} checks passed", end="")
if failed == 0:
    print(" — FULLY FUNCTIONAL")
else:
    print(f" | {failed} need attention")
print("=" * 60)

# Catalog count
pw = urllib.parse.unquote('GrantPro2026%21Secure')
conn = psycopg2.connect(host='aws-1-us-east-1.pooler.supabase.com', port=6543, dbname='postgres', user='postgres.mubghncbtnkjkywbcfts', password=pw)
conn.autocommit = True
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM grants_catalog WHERE status IN ('posted','forecasted')")
total_cat = c.fetchone()[0]
conn.close()
print(f"\n  Live catalog: {total_cat:,} posted/forecasted grants")
