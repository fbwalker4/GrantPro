import requests, re
s = requests.Session()
r = s.get('https://grantpro.org/login', timeout=20)
csrf = re.search(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', r.text).group(1)
r = s.post('https://grantpro.org/login', data={
    'email': 'qa_paid_coastalhousing@test.com',
    'password': 'GrantPro2026!',
    'csrf_token': csrf
}, timeout=20, allow_redirects=True)
cookie = dict(s.cookies).get('session', '')
with open('/tmp/grantpro_session.txt', 'w') as f:
    f.write(cookie)
print(f"URL: {r.url}, cookie_len: {len(cookie)}")
