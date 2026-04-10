#!/usr/bin/env python3
"""Debug mark_submitted CSRF issue."""
import requests, re, psycopg2, urllib.parse

BASE_URL = "https://grantpro.org"
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

def get_csrf(html):
    m = re.search(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', html)
    return m.group(1) if m else ""

# Login
r = session.get(f"{BASE_URL}/login", timeout=30)
resp = session.post(f"{BASE_URL}/login", data={
    'email': 'qa_paid_coastalhousing@test.com',
    'password': 'GrantPro2026!',
    'csrf_token': get_csrf(r.text)
}, timeout=30, allow_redirects=True)
print("Logged in:", resp.url)

grant_id = "grant-20260410-013501-c4be33e4"

# Get the mark-submitted page (GET form)
r = session.get(f"{BASE_URL}/grant/{grant_id}/mark-submitted", timeout=30)
print(f"\nGET /mark-submitted: status={r.status_code}, url={r.url}")
csrf = get_csrf(r.text)
print(f"CSRF token: '{csrf[:30]}...' (len={len(csrf)})")
print(f"Session cookies: {dict(session.cookies)}")

# Check what the page contains
if 'Access denied' in r.text:
    print("ACCESS DENIED on GET!")
elif 'paid' in r.text.lower():
    print("PAID REQUIRED redirect")
else:
    print("Page loaded OK")

# Try POST with and without the CSRF
print("\n--- POST without allow_redirects ---")
resp_no_redir = session.post(
    f"{BASE_URL}/grant/{grant_id}/mark-submitted",
    data={
        'csrf_token': csrf,
        'submission_date': '2026-04-09',
        'confirmation_number': 'E2E-FHLB-2026',
        'portal_used': 'Direct',
        'notes': 'E2E test'
    },
    timeout=30,
    allow_redirects=False
)
print(f"Status: {resp_no_redir.status_code}")
print(f"Location header: {resp_no_redir.headers.get('Location', 'none')}")
print(f"Response snippet: {resp_no_redir.text[:300]}")

# Check DB after POST
pw = urllib.parse.unquote('GrantPro2026%21Secure')
conn = psycopg2.connect(host='aws-1-us-east-1.pooler.supabase.com', port=6543, dbname='postgres', user='postgres.mubghncbtnkjkywbcfts', password=pw)
conn.autocommit = True
c = conn.cursor()
c.execute("SELECT status, submitted_at FROM grants WHERE id = %s", (grant_id,))
row = c.fetchone()
conn.close()
if row:
    print(f"\nDB state: status={row[0]}, submitted_at={row[1]}")
