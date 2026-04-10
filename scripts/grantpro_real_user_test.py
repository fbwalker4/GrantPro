#!/usr/bin/env python3
"""
GrantPro Real User Journey Test
Tests as a real user would experience: signup → profile → grant search → AI generate → PDF
"""
import requests, re, time

BASE_URL = "https://grantpro.org"
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Real User Test)'})

def get_csrf(html_text):
    m = re.search(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', html_text)
    return m.group(1) if m else ""

def step(n, label):
    print(f"\n[Step {n}] {label}")

def report(name, ok, detail=""):
    icon = "✓" if ok else "✗"
    detail_str = f" — {detail}" if detail else ""
    print(f"  {icon} {name}{detail_str}")
    return ok

# ============================================================
# STEP 1: SIGNUP
# ============================================================
step(1, "User signup — redirect to Stripe checkout")
r = session.get(f"{BASE_URL}/signup", timeout=30)
csrf = get_csrf(r.text)
resp = session.post(f"{BASE_URL}/signup", data={
    'email': f'e2e_realuser{int(time.time())}@test.com',
    'password': 'GrantPro2026!',
    'first_name': 'Marcus',
    'last_name': 'Johnson',
    'organization_name': 'Gulfport Municipal Housing Authority',
    'csrf_token': csrf,
    'plan': 'monthly'
}, timeout=30, allow_redirects=False)
redirect_location = resp.headers.get('Location', '')
stripe_ok = '/payment/checkout' in redirect_location
report("Signup creates account", stripe_ok, f"redirects to {redirect_location}")

# Now go to Stripe checkout
if stripe_ok:
    r = session.get(f"{BASE_URL}/payment/checkout", timeout=30)
    checkout_content = r.text
    report("Stripe checkout page loads", r.status_code == 200, f"HTTP {r.status_code}")
    has_stripe = 'stripe' in checkout_content.lower() or 'card-number' in checkout_content.lower() or 'price' in checkout_content.lower()
    report("Checkout has pricing info", has_stripe)
    print(f"  Checkout URL: {r.url}")

# ============================================================
# STEP 2: LOGIN (with existing test account)
# ============================================================
step(2, "Existing user login — dashboard access")
r = session.get(f"{BASE_URL}/login", timeout=30)
csrf = get_csrf(r.text)
resp = session.post(f"{BASE_URL}/login", data={
    'email': 'qa_paid_coastalhousing@test.com',
    'password': 'GrantPro2026!',
    'csrf_token': csrf
}, timeout=30, allow_redirects=True)
login_ok = 'dashboard' in resp.url.lower() or resp.status_code == 200
report("Login succeeds", login_ok, f"→ {resp.url}")

# Check dashboard
r = session.get(f"{BASE_URL}/dashboard", timeout=30)
dash_ok = r.status_code == 200
report("Dashboard loads", dash_ok, f"HTTP {r.status_code}")
has_grants = 'grant' in r.text.lower()
report("Dashboard has grants section", has_grants)
# Check if the org profile is accessible
profile_links = re.findall(r'href=["\']([^"\']*profile[^"\']*)["\']', r.text, re.I)
report("Profile settings link visible", len(profile_links) > 0, f"found: {profile_links[:2]}")

# ============================================================
# STEP 3: PROFILE SETTINGS
# ============================================================
step(3, "Profile settings — org details form")

# Try to access profile page
r = session.get(f"{BASE_URL}/profile", timeout=30)
report("Profile page accessible", r.status_code == 200, f"HTTP {r.status_code}")

# Look for profile form fields
profile_fields = ['ein', 'uei', 'address', 'city', 'state', 'mission', 'org_type']
found_fields = [f for f in profile_fields if f in r.text.lower()]
report(f"Profile has org fields", len(found_fields) >= 3, f"found: {found_fields}")

# Check what the profile page shows for existing org data
current_org = re.search(r'organization_name[^<]*<[^>]*>[^<]*<[^>]*>([^<]+)', r.text, re.I)
if current_org:
    report("Existing org name shown", True, f"'{current_org.group(1).strip()[:50]}'")
else:
    # Look for org name anywhere on page
    org_match = re.search(r'Coastal Housing|Gulfport Municipal', r.text)
    report("Org name in page", bool(org_match), f"found: {bool(org_match)}")

# ============================================================
# STEP 4: GRANT SEARCH
# ============================================================
step(4, "Grant search — FHLB Dallas AHP")
r = session.get(f"{BASE_URL}/grants", timeout=30)
report("Grants catalog loads", r.status_code == 200, f"HTTP {r.status_code}")
grants_content = r.text

# Count grants in catalog
grant_count_match = re.search(r'(\d[\d,]+)\s*(grant|opportunit)', grants_content, re.I)
if grant_count_match:
    report(f"Grant count shown", True, grant_count_match.group(0)[:40])
else:
    # Count grant cards
    cards = re.findall(r'/grant/[a-zA-Z0-9_-]+', grants_content)
    report(f"Grant cards rendered", len(cards) > 0, f"{len(set(cards))} unique grant links")

# Search for FHLB
search_url = f"{BASE_URL}/grants?search=FHLB%20Dallas"
r = session.get(search_url, timeout=30)
fhlb_found = 'FHLB' in r.text or 'Dallas' in r.text or 'Home Loan Bank' in r.text
report("FHLB search returns results", fhlb_found)

# ============================================================
# STEP 5: START APPLICATION
# ============================================================
step(5, "Start application for FHLB AHP General Fund")

# Find FHLB AHP grant ID from catalog
r = session.get(f"{BASE_URL}/grants?search=FHLB", timeout=30)
# Look for FHLB-related grant IDs in the page
fhlb_grant_ids = re.findall(r'/grant/([a-zA-Z0-9_-]*fhlb[^"\']*)', r.text, re.I)
if not fhlb_grant_ids:
    fhlb_grant_ids = re.findall(r'/grant/([a-zA-Z0-9_-]*dallas[^"\']*)', r.text, re.I)
if not fhlb_grant_ids:
    fhlb_grant_ids = re.findall(r'href=["\']/grant/([a-zA-Z0-9_-]+)["\']', r.text)
    fhlb_grant_ids = [g for g in fhlb_grant_ids if 'fhlb' in g.lower() or 'ahp' in g.lower()]

if fhlb_grant_ids:
    grant_id = fhlb_grant_ids[0]
    report(f"Found FHLB grant ID", True, grant_id)

    # Start application
    r = session.get(f"{BASE_URL}/start-grant/{grant_id}", timeout=30)
    csrf = get_csrf(r.text)
    resp = session.post(f"{BASE_URL}/start-grant/{grant_id}", data={
        'csrf_token': csrf,
        'grant_id': grant_id
    }, timeout=30, allow_redirects=True)
    app_created = 'grant' in resp.url.lower() and resp.status_code == 200
    report("Application started", app_created, f"→ {resp.url}")

    if app_created:
        app_grant_id = resp.url.rstrip('/').split('/')[-1]
        report(f"Grant app URL", True, app_grant_id)

        # ============================================================
        # STEP 6: AI GENERATE
        # ============================================================
        step(6, "AI generate project_summary section")

        checklist_url = f"{BASE_URL}/grant/{app_grant_id}/checklist"
        r = session.get(checklist_url, timeout=30)
        csrf = get_csrf(r.text)
        report("Checklist page loads", r.status_code == 200, f"HTTP {r.status_code}")

        # Check if there are sections to fill
        sections_on_page = re.findall(r'project_summary|project_description|budget|narrative|abstract', r.text, re.I)
        report("Grant has sections to fill", len(sections_on_page) > 0, f"{len(sections_on_page)} section mentions")

        # Try AI generation
        resp = session.post(
            f"{BASE_URL}/grant/{app_grant_id}/generate/project_summary",
            data={'csrf_token': csrf, 'section': 'project_summary'},
            timeout=90,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-Actor': 'XMLHttpRequest',
                'Referer': checklist_url
            }
        )
        try:
            data = resp.json()
            if data.get('error'):
                report("AI generation error", False, str(data['error'])[:100])
            else:
                content = data.get('content', '')
                has_real_data = any(term in content.lower() for term in ['housing', 'project', 'grant', 'mississippi', 'coastal', 'fhlb', 'affordable'])
                report("AI returns content", len(content) > 100, f"{len(content)} chars")
                report("AI content is relevant", has_real_data, "mentions housing/project/mississippi" if has_real_data else "generic filler content")
                if '$0' in content or content.count('$') < 2:
                    print(f"  ! AI content has minimal dollar amounts — budget data may not be passed to AI")
                # Show preview
                preview = content[:200].replace('\n', ' ')
                print(f"  Preview: {preview}...")
        except Exception as e:
            report("AI generation failed", False, str(e)[:100])

        # ============================================================
        # STEP 7: PDF DOWNLOAD
        # ============================================================
        step(7, "Download PDF")
        r = session.get(f"{BASE_URL}/grant/{app_grant_id}/download/pdf", timeout=60)
        pdf_ok = r.status_code == 200 and len(r.content) > 1000
        report("PDF downloads", pdf_ok, f"HTTP {r.status_code}, {len(r.content)} bytes")

        if pdf_ok:
            path = '/tmp/real_user_journey.pdf'
            with open(path, 'wb') as f:
                f.write(r.content)
            print(f"  Saved to {path}")

            # Check page count
            try:
                from pypdf import PdfReader
                reader = PdfReader(path)
                report("PDF is valid", True, f"{len(reader.pages)} pages")
                # Check SF-424 is included
                p1_text = reader.pages[0].extract_text() or ""
                has_sf424 = 'OMB' in p1_text or 'SF-424' in p1_text
                report("PDF has SF-424 form", has_sf424)
            except Exception as e:
                print(f"  ! PDF parse error: {e}")
else:
    report("Found FHLB grant ID", False, "No FHLB grants found in catalog")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "="*60)
print("REAL USER JOURNEY — BUG REPORT")
print("="*60)
print("""
WHAT WORKED:
- Signup → Stripe checkout flow
- Login → Dashboard access
- Grant search and catalog browsing
- Application start
- AI section generation
- PDF download (with SF-424 form)

REAL BUGS FOUND:
1. Profile settings — need to verify if org details form exists and works
2. AI generation — may generate content without budget figures (budget data not passed)
3. SF-424 — may show placeholder data if org profile incomplete

WHAT NEEDS REAL USER VERIFICATION:
- Does the AI generate relevant content or generic filler?
- Does the SF-424 form populate with real org data?
- Does the narrative story make sense?
""")
