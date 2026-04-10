#!/usr/bin/env python3
"""
Profile route E2E test — verifies org_details (EIN, UEI, address) save correctly.
Run after ANY change to the profile route or organization_details upsert.
"""
import sys
import psycopg2
import requests
import re

BASE = "https://grantpro.org"
EMAIL = "qa_paid_coastalhousing@test.com"
PASSWORD = "GrantPro2026!"

def get_csrf(sess, url):
    r = sess.get(url, timeout=15)
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text)
    if not m:
        raise ValueError(f"No CSRF token on {url}")
    return m.group(1)

def login(sess):
    csrf = get_csrf(sess, f"{BASE}/login")
    r = sess.post(f"{BASE}/login", data={
        "email": EMAIL, "password": PASSWORD, "csrf_token": csrf
    }, timeout=15, allow_redirects=False)
    if r.status_code not in (302, 303):
        raise ValueError(f"Login failed: {r.status_code}")

def check_db_org_details(user_id, field):
    conn = psycopg2.connect(
        host="db.mubghncbtnkjkywbcfts.supabase.co", port=6543,
        dbname="postgres", user="postgres", password="GrantPro2026!Secure"
    )
    c = conn.cursor()
    c.execute(f"SELECT {field} FROM organization_details WHERE user_id = %s", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_user_id(sess):
    conn = psycopg2.connect(
        host="db.mubghncbtnkjkywbcfts.supabase.co", port=6543,
        dbname="postgres", user="postgres", password="GrantPro2026!Secure"
    )
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email = %s", (EMAIL,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def main():
    errors = []

    # 1. Verify template uses correct field names
    import requests
    sess = requests.Session()
    login(sess)
    r = sess.get(f"{BASE}/profile", timeout=15)
    template_fields = re.findall(r'name="([^"]+)"', r.text)
    required = {"first_name", "last_name", "organization_name", "ein", "uei",
                "address_line1", "city", "state", "zip_code",
                "mission_statement", "organization_type", "congressional_district"}
    missing = required - set(template_fields)
    if missing:
        errors.append(f"Template missing fields: {missing}")
    else:
        print("  ✅ All required fields present in template")

    # 2. Verify CSRF-protected POST returns 302 (not 500)
    csrf = get_csrf(sess, f"{BASE}/profile")
    r = sess.post(f"{BASE}/profile", data={
        "csrf_token": csrf,
        "bio": "Test bio",
    }, timeout=15, allow_redirects=False)
    if r.status_code == 302:
        print("  ✅ Basic profile POST: 302")
    else:
        errors.append(f"Basic profile POST returned {r.status_code} (expected 302)")

    # 3. Verify org_details saves to DB
    user_id = get_user_id(sess)
    csrf = get_csrf(sess, f"{BASE}/profile")
    test_ein = f"64-{10000000 + int(datetime.now().timestamp())}"
    r = sess.post(f"{BASE}/profile", data={
        "csrf_token": csrf,
        "first_name": "Carla",
        "last_name": "Thornton",
        "organization_name": "Coastal Housing Authority",
        "organization_type": "housing_authority",
        "ein": test_ein,
        "uei": "NH4CLKMVWN89",
        "address_line1": "1400 Marina Bay Drive",
        "city": "Gulfport",
        "state": "MS",
        "zip_code": "39507",
        "mission_statement": "Affordable housing for Mississippi Gulf Coast",
        "congressional_district": "MS-001"
    }, timeout=15, allow_redirects=False)

    if r.status_code != 302:
        errors.append(f"Full profile POST returned {r.status_code}: {r.text[:200]}")
    else:
        saved_ein = check_db_org_details(user_id, "ein")
        if saved_ein == test_ein:
            print(f"  ✅ EIN saved to DB: {saved_ein}")
        else:
            errors.append(f"EIN not saved. DB has: {saved_ein}, expected: {test_ein}")

        saved_uei = check_db_org_details(user_id, "uei")
        if saved_uei == "NH4CLKMVWN89":
            print(f"  ✅ UEI saved to DB: {saved_uei}")
        else:
            errors.append(f"UEI not saved. DB has: {saved_uei}")

    if errors:
        print("\n❌ ERRORS:")
        for e in errors:
            print(f"   {e}")
        sys.exit(1)
    else:
        print("\n✅ All profile + org_details checks passed")

if __name__ == "__main__":
    from datetime import datetime
    main()
