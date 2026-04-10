#!/usr/bin/env python3
"""Debug the SF-424 generation in the download route."""
import sys, os, requests, re, traceback

sys.path.insert(0, '/Users/fbwalker4/.hermes/grant-system/core')
sys.path.insert(0, '/Users/fbwalker4/.hermes/grant-system')
os.chdir('/Users/fbwalker4/.hermes/grant-system')

# Set env before imports
os.environ['GP_DATABASE_URL'] = 'postgresql://postgres.mubghncbtnkjkywbcfts:GrantPro2026%21Secure@aws-1-us-east-1.pooler.supabase.com:6543/postgres'

from core.db_connection import get_connection
from core import user_models
from core import budget_builder
from io import BytesIO
from reportlab.lib.pagesizes import letter

BASE_URL = "https://grantpro.org"
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

# Login
r = session.get(f"{BASE_URL}/login", timeout=30)
csrf_m = re.search(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', r.text)
session.post(f"{BASE_URL}/login", data={
    'email': 'qa_paid_coastalhousing@test.com', 'password': 'GrantPro2026!',
    'csrf_token': csrf_m.group(1) if csrf_m else ''
}, timeout=30, allow_redirects=True)
print("Logged in")

GRANT_ID = "grant-20260410-013501-c4be33e4"

# Replicate exactly what the download route does
conn = get_connection()

# Get user from session (we know the email)
c = conn.cursor()
c.execute("SELECT * FROM users WHERE email = %s", ('qa_paid_coastalhousing@test.com',))
user = dict(c.fetchone())
print(f"User: {user['email']}, plan={user['plan']}")

# Get org details
user_org_details = user_models.get_organization_details(user['id'])
print(f"Org details keys: {list(user_org_details.keys()) if user_org_details else 'NONE'}")

# Get grant data
c.execute("""
    SELECT g.*, c.organization_name, c.contact_name, c.contact_email,
           c.address_line1, c.city, c.state, c.zip_code, c.phone, c.website,
           c.org_type, c.mission
    FROM grants g JOIN clients c ON g.client_id = c.id
    WHERE g.id = %s
""", (GRANT_ID,))
grant_row = c.fetchone()
if not grant_row:
    print("Grant not found!")
else:
    grant = dict(grant_row)
    print(f"Grant: {grant['grant_name']}, status={grant['status']}")

    # Get budget
    budget = budget_builder.get_grant_budget(GRANT_ID)
    print(f"Budget: {budget}")

    # Build sf424_grant
    from datetime import datetime
    sf424_grant = {
        'grant_name': grant.get('grant_name',''),
        'agency': grant.get('agency',''),
        'amount': grant.get('amount', 0) or 0,
        'deadline': grant.get('deadline',''),
        'status': grant.get('status',''),
        'open_date': grant.get('open_date',''),
        'close_date': grant.get('close_date',''),
    }

    # Build sf424_org
    od = user_org_details.get('organization_details', {}) if user_org_details else {}
    op = user_org_details.get('organization_profile', {}) if user_org_details else {}
    sf424_org = {
        'legal_name': od.get('legal_name') or grant.get('organization_name',''),
        'ein': od.get('ein',''),
        'uei': od.get('uei',''),
        'street': od.get('address_line1',''),
        'city': od.get('city',''),
        'state': od.get('state',''),
        'zipcode': od.get('zip_code',''),
        'first_name': grant.get('contact_name','').split()[0] if grant.get('contact_name') else '',
        'last_name': ' '.join(grant.get('contact_name','').split()[1:]) if grant.get('contact_name') else '',
        'title': od.get('title',''),
        'telephone': od.get('phone',''),
        'email': od.get('email') or grant.get('contact_email',''),
        'contact_phone': od.get('phone',''),
        'contact_email': grant.get('contact_email',''),
        'org_type': op.get('organization_type',''),
        'website': od.get('website',''),
        'mission': op.get('mission_statement',''),
    }

    # Build sf424_budget
    sf424_budget = {
        'total': grant.get('amount', 0) or 0,
        'federal': grant.get('amount', 0) or 0,
        'non_federal': 0,
    }

    print(f"\nsf424_grant: {sf424_grant}")
    print(f"\nsf424_org legal_name: {sf424_org.get('legal_name')}")
    print(f"  ein={sf424_org.get('ein')}, uei={sf424_org.get('uei')}")
    print(f"  street={sf424_org.get('street')}, city={sf424_org.get('city')}")
    print(f"  contact_email={sf424_org.get('contact_email')}")
    print(f"\nsf424_budget: {sf424_budget}")

    # Try to generate SF-424 pages
    print("\n--- Trying generate_sf424_pages ---")
    try:
        from core.form_generator import generate_sf424_pages
        pages = generate_sf424_pages(sf424_grant, sf424_org, sf424_budget)
        print(f"SUCCESS: {len(pages)} pages generated")
        for i, page in enumerate(pages):
            print(f"  Page {i+1}: {type(page)}")
    except Exception as e:
        print(f"EXCEPTION: {e}")
        traceback.print_exc()

conn.close()
