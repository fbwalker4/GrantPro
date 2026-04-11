#!/usr/bin/env python3
import sys, os
sys.path.insert(0, '/Users/fbwalker4/.hermes/grant-system')
sys.path.insert(0, '/Users/fbwalker4/.hermes/grant-system/core')
sys.path.insert(0, '/Users/fbwalker4/.hermes/grant-system/portal')

import re

try:
    from portal.app import app
    print(f"Flask app loaded OK")
except Exception as e:
    print(f"Import error: {e}")
    sys.exit(1)

with app.test_client() as client:
    # Login
    resp = client.post('/login', data={
        'email': 'rusty@fwalker.com',
        'password': 'buttmonkeys'
    }, follow_redirects=False)
    print(f"Login: {resp.status_code} -> {resp.location}")

    # Onboarding GET
    resp2 = client.get('/onboarding')
    print(f"Onboarding GET: {resp2.status_code}")
    if resp2.status_code != 200:
        print(f"FAIL: {resp2.data[:200]}")
        sys.exit(1)

    body = resp2.data.decode('utf-8')
    csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', body)
    if not csrf_match:
        csrf_match = re.search(r'value="([^"]+)"[^>]*name="csrf_token"', body)
    csrf = csrf_match.group(1) if csrf_match else ''
    print(f"CSRF: {csrf[:20]}...")

    # Submit minimal form
    resp3 = client.post('/onboarding', data={
        'csrf_token': csrf,
        'organization_name': 'Test Org',
    }, follow_redirects=False)
    print(f"Onboarding POST: {resp3.status_code} -> {resp3.location}")
    if resp3.status_code == 500:
        print("FAIL: 500 ERROR")
        print(resp3.data[:1000].decode('utf-8', errors='replace'))
    elif resp3.status_code == 302:
        print(f"OK: Redirected to {resp3.location}")
    else:
        body3 = resp3.data.decode('utf-8', errors='replace')
        if 'flash-error' in body3:
            m = re.search(r'flash-error"[^>]*>(.*?)</div>', body3, re.DOTALL)
            print(f"Error shown: {m.group(1)[:200] if m else 'unknown'}")
        else:
            print(f"Status {resp3.status_code}, URL {resp3.location}")
