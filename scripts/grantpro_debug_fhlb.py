#!/usr/bin/env python3
"""Debug FHLB grants and profile — real user journey bugs"""
import requests, re
s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0 (Real User Test)'})
BASE_URL = "https://grantpro.org"

def get_csrf(html_text):
    m = re.search(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', html_text)
    return m.group(1) if m else ""

r = s.get(f"{BASE_URL}/login", timeout=20)
s.post(f"{BASE_URL}/login", data={'email':'qa_paid_coastalhousing@test.com','password':'GrantPro2026!','csrf_token':get_csrf(r.text)}, timeout=20, allow_redirects=True)

# === BUG 1: Grants catalog is Vue SPA — no clickable links ===
print("=== BUG 1: Grant catalog links ===")
r = s.get(f"{BASE_URL}/grants?search=FHLB", timeout=20)
cards = re.findall(r'data-title="([^"]+)"[^>]*data-agency="([^"]+)"', r.text)
print(f"Grant cards found: {len(cards)}")
for title, agency in cards[:5]:
    print(f"  [{title}] — {agency}")
# Grant IDs
ids = re.findall(r'data-id="([^"]+)"', r.text)
print(f"Grant data-ids: {ids[:5]}")
# Check if there's a grant detail URL anywhere
detail_urls = re.findall(r'/grant/[a-zA-Z0-9_-]{10,}', r.text)
print(f"Detail URLs: {detail_urls[:5] if detail_urls else 'NONE'}")

# === BUG 2: Profile shows empty org name ===
print("\n=== BUG 2: Profile page org name ===")
r = s.get(f"{BASE_URL}/profile", timeout=20)
print(f"Profile page HTTP: {r.status_code}")
# Look for org name field and its value
org_field = re.search(r'organization_name[^>]*>[^>]*>[^>]*>([^<]+)', r.text, re.I)
print(f"Org name field regex match: {org_field.group(1).strip()[:50] if org_field else 'NOT FOUND'}")
# Look for any field showing the actual org value
value_matches = re.findall(r'value="([^"]{3,50})"', r.text)
print(f"Input field values: {value_matches[:10]}")
# Check what the form fields say
field_hints = re.findall(r'placeholder="([^"]{3,50})"', r.text)
print(f"Placeholder hints: {field_hints[:10]}")

# === BUG 3: Try to access a specific grant directly ===
print("\n=== BUG 3: Direct grant access ===")
# Try the FHLB AHP grant ID from the catalog
for grant_id in ['fhlb-dallas-ahp-general-2026', 'fhlb-dallas-ahp-general']:
    r = s.get(f"{BASE_URL}/grant/{grant_id}", timeout=20)
    print(f"GET /grant/{grant_id}: HTTP {r.status_code}, url={r.url}")
    if r.status_code == 200:
        # Check if it's the grant detail page or redirect to login
        is_grant_page = 'agency' in r.text.lower() and ('grant' in r.text.lower() or 'application' in r.text.lower())
        print(f"  Looks like grant detail: {is_grant_page}")
        break
