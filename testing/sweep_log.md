# Sweep Log

- 2026-04-12T21:30:35Z | portal/app.py | Issue: public copy on grant-count fallback read awkwardly and could show bad phrasing across pages. Fix: changed fallback wording to "Thousands of" and verified landing/pricing/help/upgrade render without template errors.
- 2026-04-12T21:39:02Z | /login, /admin, /dashboard, /payment/* | Issue found: no new blocker; admin login works when CSRF token is present, protected routes redirect correctly, and payment/upgrade routes return expected redirects/pages. Fix made: none. Verification: live HTTP checks passed for admin auth, dashboard, admin surface, and payment redirect paths.
- 2026-04-12T21:47:11Z | /api/health | Issue found: health endpoint was missing and returned 404, breaking E2E smoke. Fix made: added compatibility /api/health route in portal/app.py and restarted the local server. Verification: curl now returns 200 {"status":"ok"}; smoke suite can use the endpoint again.
