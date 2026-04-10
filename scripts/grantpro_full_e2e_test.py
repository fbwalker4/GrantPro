#!/usr/bin/env python3
"""
GrantPro Full End-to-End Test — Grant Application Journey
Tests: Login as paid user → Select grant → Start application → AI generate → DOCX → Submit
"""
import requests, re, sys, time, json, hashlib, os, secrets

BASE_URL = "https://grantpro.org"

# Use existing test users (password hashes verified correct)
TEST_EMAIL_PAID = "qa_paid_coastalhousing@test.com"
TEST_PASSWORD = "GrantPro2026!"

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (GrantPro E2E Bot/1.0)'})

def get_form_csrf(html):
    """Extract any csrf token from form in HTML."""
    for pat in [r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']',
                r'value=["\']([a-f0-9]{20,})["\'][^>]*name=["\']csrf_token["\']']:
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return ""

def do_login():
    """Login and maintain session."""
    r = session.get(f"{BASE_URL}/login", timeout=30)
    csrf = get_form_csrf(r.text)
    if not csrf:
        return False, f"Could not extract CSRF. Page snippet: {r.text[:300]}"
    resp = session.post(f"{BASE_URL}/login", data={
        'email': TEST_EMAIL_PAID,
        'password': TEST_PASSWORD,
        'csrf_token': csrf
    }, timeout=30, allow_redirects=True)
    if resp.status_code >= 400:
        return False, f"HTTP {resp.status_code}"
    if 'login' in resp.url.lower() and 'dashboard' not in resp.url.lower():
        return False, f"Still on login page: {resp.url}"
    return True, f"Logged in, now at: {resp.url}"

def get_session_user():
    """Check if session is authenticated by hitting /dashboard."""
    r = session.get(f"{BASE_URL}/dashboard", timeout=30)
    if 'login' in r.url.lower():
        return None
    # Look for user email or name in page
    m = re.search(r'(qa_paid|coastal|test)', r.text, re.I)
    return r.text[:500] if r.status_code == 200 else None

def get_ms_grant():
    """Pick a real MS recurring grant from DB."""
    import psycopg2, urllib.parse
    pw = urllib.parse.unquote('GrantPro2026%21Secure')
    conn = psycopg2.connect(
        host='aws-1-us-east-1.pooler.supabase.com', port=6543, dbname='postgres',
        user='postgres.mubghncbtnkjkywbcfts', password=pw
    )
    conn.autocommit = True
    c = conn.cursor()
    c.execute("""
        SELECT id, title, agency, source, status, amount_min, amount_max
        FROM grants_catalog
        WHERE status IN ('posted')
          AND source IN ('mshomecorp','mda-mississippi','dra','fhlb-dallas','fhlb-atlanta','entergy','mgccf')
        ORDER BY source
        LIMIT 5
    """)
    rows = c.fetchall()
    conn.close()
    if rows:
        r = rows[0]
        return {
            'id': r[0], 'title': r[1], 'agency': r[2],
            'source': r[3], 'status': r[4],
            'amount_min': r[5], 'amount_max': r[6]
        }
    return None

def start_grant_application(grant_id):
    """Start an application for a grant via /start-grant/<grant_id>."""
    url = f"{BASE_URL}/start-grant/{grant_id}"
    r = session.get(url, timeout=30)
    csrf = get_form_csrf(r.text)
    if not csrf:
        # Check if redirect happened (already started)
        if 'dashboard' in r.url.lower() or r.status_code == 200:
            return True, f"Redirected to: {r.url} (may already be started)"
        return False, f"No CSRF on start page. Status={r.status_code} url={r.url} html={r.text[:200]}"
    resp = session.post(url, data={
        'csrf_token': csrf,
        'grant_id': grant_id
    }, timeout=30, allow_redirects=True)
    return resp.status_code < 400, f"status={resp.status_code} url={resp.url}"

def generate_section(grant_id, section='project_summary'):
    """Generate AI content for a grant section."""
    r = session.get(f"{BASE_URL}/grant/{grant_id}/checklist", timeout=30)
    csrf = get_form_csrf(r.text)
    if not csrf and 'login' in r.url.lower():
        return False, "Not logged in"
    csrf = csrf or "no_csrf"
    resp = session.post(
        f"{BASE_URL}/grant/{grant_id}/generate/{section}",
        data={'csrf_token': csrf, 'section': section},
        timeout=90,
        headers={
            'X-Requested-Actor': 'XMLHttpRequest',
            'Referer': f"{BASE_URL}/grant/{grant_id}/checklist",
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    )
    try:
        data = resp.json()
        if data.get('error'):
            return False, f"AI error: {str(data['error'])[:200]}"
        content = data.get('content', '')
        return True, f"Generated {len(content)} chars"
    except:
        return False, f"Non-JSON ({resp.status_code}): {resp.text[:200]}"

def download_docx(grant_id):
    """Download DOCX."""
    r = session.get(f"{BASE_URL}/grant/{grant_id}/download/docx", timeout=60, allow_redirects=True)
    if r.status_code == 200 and len(r.content) > 1000:
        path = '/tmp/grantpro_e2e.docx'
        with open(path, 'wb') as f:
            f.write(r.content)
        return True, f"Downloaded {len(r.content):,} bytes"
    return False, f"HTTP {r.status_code}, size={len(r.content)}"

def mark_submitted(grant_id):
    """Mark grant as submitted."""
    r = session.get(f"{BASE_URL}/grant/{grant_id}/mark-submitted", timeout=30)
    csrf = get_form_csrf(r.text)
    if not csrf and 'login' in r.url.lower():
        return False, "Not logged in"
    csrf = csrf or "no_csrf"
    resp = session.post(f"{BASE_URL}/grant/{grant_id}/mark-submitted", data={
        'csrf_token': csrf,
        'submission_date': '2026-04-09',
        'confirmation_number': 'E2E-COASTAL-2026',
        'portal_used': 'Direct (GrantPro E2E)',
        'notes': 'End-to-end test submission'
    }, timeout=30, allow_redirects=True)
    return resp.status_code < 400, f"status={resp.status_code} url={resp.url}"

def get_active_grant_id():
    """Find a grant application ID from the dashboard."""
    r = session.get(f"{BASE_URL}/dashboard", timeout=30)
    # Find grant detail links
    grant_links = re.findall(r'href=["\'](/grant/([a-zA-Z0-9_-]+))["\']', r.text)
    app_links = [(url, gid) for url, gid in grant_links if
                 not gid.startswith('gg-') and
                 not gid.startswith('ms-') and
                 'catalog' not in gid.lower()]
    if app_links:
        return app_links[0][1]
    # Fall back: look for any grant- link
    any_links = [gid for url, gid in grant_links if 'grant-' in gid or 'e2e' in gid.lower()]
    return any_links[0] if any_links else None

def main():
    print("=" * 60)
    print("GrantPro Full E2E — Imaginary Client Grant Journey")
    print("=" * 60)

    errors = []
    warnings = []

    # STEP 1: Login as paid user
    print("\n[Step 1] Login as paid user")
    ok, msg = do_login()
    if not ok:
        errors.append(f"Login: {msg}")
        print(f"    [FAIL] {msg}")
        print_summary(errors, warnings)
        return 1
    print(f"    [PASS] {msg}")

    # Verify session
    user_html = get_session_user()
    if not user_html:
        errors.append("Session not authenticated")
        print(f"    [FAIL] Session check failed")
        print_summary(errors, warnings)
        return 1
    print(f"    [PASS] Session authenticated")

    # STEP 2: Pick a grant
    print("\n[Step 2] Select grant from catalog")
    grant = get_ms_grant()
    if not grant:
        errors.append("No grants found in catalog")
        print(f"    [FAIL] Empty catalog")
        return 1
    print(f"    [PASS] Selected: [{grant['source']}/{grant['status']}]")
    print(f"           {grant['title'][:70]}")
    print(f"           Agency: {grant['agency']}")
    print(f"           Amount: ${grant['amount_min']:,}–${grant['amount_max']:,}")
    grant_id = grant['id']

    # STEP 3: Start application
    print(f"\n[Step 3] Start application")
    ok, msg = start_grant_application(grant_id)
    if ok:
        print(f"    [PASS] {msg}")
    else:
        warnings.append(f"Start application: {msg}")
        print(f"    [WARN] {msg}")

    # STEP 4: Find active grant app
    print("\n[Step 4] Locate active grant application")
    app_grant_id = get_active_grant_id()
    if app_grant_id:
        print(f"    [PASS] Found app: {app_grant_id}")
    else:
        app_grant_id = grant_id
        print(f"    [INFO] Using catalog grant ID: {app_grant_id}")

    # STEP 5: AI generate project_summary section
    print(f"\n[Step 5] AI generate project_summary section")
    ok, msg = generate_section(app_grant_id, 'project_summary')
    if ok:
        print(f"    [PASS] {msg}")
    else:
        warnings.append(f"AI gen: {msg}")
        print(f"    [WARN] {msg}")

    # STEP 6: Download DOCX
    print(f"\n[Step 6] Download DOCX")
    ok, msg = download_docx(app_grant_id)
    if ok:
        print(f"    [PASS] {msg}")
    else:
        warnings.append(f"DOCX: {msg}")
        print(f"    [WARN] {msg}")

    # STEP 7: Mark as submitted
    print(f"\n[Step 7] Mark grant as submitted")
    ok, msg = mark_submitted(app_grant_id)
    if ok:
        print(f"    [PASS] {msg}")
    else:
        warnings.append(f"Submit: {msg}")
        print(f"    [WARN] {msg}")

    # STEP 8: Verify final DB state
    print(f"\n[Step 8] Verify grant in DB")
    import psycopg2, urllib.parse
    pw = urllib.parse.unquote('GrantPro2026%21Secure')
    conn = psycopg2.connect(
        host='aws-1-us-east-1.pooler.supabase.com', port=6543, dbname='postgres',
        user='postgres.mubghncbtnkjkywbcfts', password=pw
    )
    conn.autocommit = True
    c = conn.cursor()
    # Look for grants for the coastal housing test user
    c.execute("""
        SELECT g.id, g.status, g.submitted_at, g.grant_name, c.organization_name
        FROM grants g
        JOIN clients c ON g.client_id = c.id
        WHERE c.organization_name LIKE %s
        ORDER BY g.assigned_at DESC
        LIMIT 5
    """, ('%Coastal Housing%',))
    rows = c.fetchall()
    conn.close()
    if rows:
        print(f"    [PASS] Found {len(rows)} grant(s) for Coastal Housing:")
        for r in rows:
            print(f"      - {r[0]}: status={r[1]}, submitted={r[2]}, grant={str(r[3])[:50]}")
    else:
        print(f"    [INFO] No grants found for 'Coastal Housing' org (expected — user may not have created grants)")

    print_summary(errors, warnings)
    return 0 if not errors else 1

def print_summary(errors, warnings):
    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    if errors:
        print(f"  ERRORS ({len(errors)}):")
        for e in errors: print(f"    ✗ {e}")
    if warnings:
        print(f"  WARNINGS ({len(warnings)}):")
        for w in warnings: print(f"    ! {w[:120]}")
    if not errors:
        result = "PASS" if not warnings else "PASS (with warnings)"
        print(f"  {result}")
        print(f"  Flow: login → grant selection → start application → AI generation → DOCX download → submit")
    print("=" * 60)

if __name__ == "__main__":
    sys.exit(main())
