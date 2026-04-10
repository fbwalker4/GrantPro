#!/usr/bin/env python3
"""Test profile POST using Flask test client against real Supabase DB."""
import sys, os, time
sys.path.insert(0, '/Users/fbwalker4/.hermes/grant-system')

# Must set GP_DATABASE_URL before importing app
os.environ['GP_DATABASE_URL'] = 'postgres://postgres:GrantPro2026!Secure@db.mubghncbtnkjkywbcfts.supabase.co:6543/postgres'

from portal.app import app, get_connection
import psycopg2

USER_ID = 'user-paid-20260409123743-2dafa8ff'
EMAIL = 'qa_paid_coastalhousing@test.com'

# First, set a known EIN
conn = psycopg2.connect(host='db.mubghncbtnkjkywbcfts.supabase.co', port=6543, dbname='postgres', user='postgres', password='GrantPro2026!Secure')
c = conn.cursor()
c.execute('UPDATE organization_details SET ein=%s WHERE user_id=%s', ('99-BEFORE-TEST', USER_ID))
conn.commit()
c.execute('SELECT ein FROM organization_details WHERE user_id=%s', (USER_ID,))
print('EIN before:', c.fetchone()[0])
conn.close()

# Now use Flask test client
with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['user_id'] = USER_ID
        sess['email'] = EMAIL
        sess['plan'] = 'enterprise_5'
        sess['csrf_token'] = 'test-csrf-123'
        sess['_fresh'] = True

    # Get CSRF token from profile page
    rv = client.get('/profile')
    print('Profile GET:', rv.status_code)

    # Extract CSRF from rendered page
    import re
    csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', rv.text)
    csrf_token = csrf_match.group(1) if csrf_match else 'test-csrf-123'
    print('CSRF token from page:', csrf_token[:15] + '...')

    # POST profile update
    rv = client.post('/profile', data={
        'csrf_token': csrf_token,
        'first_name': 'Carla',
        'last_name': 'Thornton',
        'organization_name': 'Coastal Housing Authority',
        'organization_type': 'housing_authority',
        'ein': '99-AFTER-TEST',
        'uei': 'TESTUEI123X',
        'address_line1': '123 Test Blvd',
        'city': 'TestCity',
        'state': 'MS',
        'zip_code': '39500',
        'mission_statement': 'Test mission statement',
        'congressional_district': 'MS-001',
    }, follow_redirects=False)

    print('Profile POST status:', rv.status_code)
    print('Redirect location:', rv.headers.get('Location', 'none'))

    time.sleep(0.5)

# Check DB
conn2 = psycopg2.connect(host='db.mubghncbtnkjkywbcfts.supabase.co', port=6543, dbname='postgres', user='postgres', password='GrantPro2026!Secure')
c2 = conn2.cursor()
c2.execute('SELECT ein, uei, address_line1 FROM organization_details WHERE user_id=%s', (USER_ID,))
result = c2.fetchone()
print('EIN after:', result[0] if result else 'ROW NOT FOUND')
print('UEI after:', result[1] if result else 'N/A')
print('Address after:', result[2] if result else 'N/A')
conn2.close()
