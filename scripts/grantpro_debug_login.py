#!/usr/bin/env python3
"""Debug login - check user in production DB."""
import sys, os
sys.path.insert(0, '/Users/fbwalker4/.hermes/grant-system/core')

os.environ['GP_DATABASE_URL'] = 'postgresql://postgres.mubghncbtnkjkywbcfts:GrantPro2026%21Secure@aws-1-us-east-1.pooler.supabase.com:6543/postgres'

from db_connection import get_connection
import hashlib, hmac

def verify_password(password, stored):
    try:
        salt, pwd_hash = stored.split('$')
        verify_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        return hmac.compare_digest(verify_hash, pwd_hash)
    except:
        return False

conn = get_connection()
c = conn.cursor()

for email in ['qa_paid_coastalhousing@test.com', 'e2e_imaginary_client@test.com', 'qa_free_fresh2026@test.com']:
    c.execute('SELECT id, email, password_hash, plan FROM users WHERE email = %s', (email,))
    row = c.fetchone()
    if row:
        print(f"User: {row['email']}, plan={row['plan']}")
        print(f"  Hash: {row['password_hash'][:60]}")
        ok = verify_password('GrantPro2026!', row['password_hash'])
        print(f"  Verify 'GrantPro2026!': {ok}")
    else:
        print(f"User {email}: NOT FOUND")
    print()

conn.close()
