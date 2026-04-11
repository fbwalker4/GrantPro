#!/usr/bin/env python3
"""GrantPro smoke test.

Checks core authenticated/public flows and prints concise PASS/FAIL output.
"""
from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass
from typing import List, Tuple

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5001"
EMAIL = sys.argv[2] if len(sys.argv) > 2 else "rusty@fwalker.com"
PASSWORD = sys.argv[3] if len(sys.argv) > 3 else "buttmonkeys"


@dataclass
class Result:
    name: str
    ok: bool
    detail: str


def csrf_from(html: str) -> str:
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    if not m:
        raise RuntimeError("No CSRF token found")
    return m.group(1)


def main() -> int:
    s = requests.Session()
    results: List[Result] = []

    def check(name: str, ok: bool, detail: str = ""):
        results.append(Result(name, ok, detail))

    try:
        r = s.get(f"{BASE}/login", timeout=20)
        tok = csrf_from(r.text)
        r = s.post(f"{BASE}/login", data={"email": EMAIL, "password": PASSWORD, "csrf_token": tok}, timeout=20, allow_redirects=False)
        check("login", r.status_code in (302, 303), f"status={r.status_code}")

        dash = s.get(f"{BASE}/dashboard", timeout=30)
        check("dashboard", dash.status_code == 200, f"status={dash.status_code}")

        grants = s.get(f"{BASE}/grants", timeout=60)
        check("grants", grants.status_code == 200 and len(grants.text) < 500_000, f"status={grants.status_code} len={len(grants.text)}")

        search = s.get(f"{BASE}/search?q=hud", timeout=60)
        check("search", search.status_code == 200 and "Apply Filters" in search.text, f"status={search.status_code} len={len(search.text)}")

        public = s.get(f"{BASE}/search", timeout=60)
        check("search_default", public.status_code == 200 and len(public.text) < 500_000, f"status={public.status_code} len={len(public.text)}")

        gr = s.get(f"{BASE}/grants", timeout=60)
        tok2 = csrf_from(gr.text)
        r = s.post(f"{BASE}/api/save-grant", json={"grant_id": "286103"}, headers={"X-CSRF-Token": tok2}, timeout=20)
        check("save_grant", r.status_code == 200, f"status={r.status_code}")
        r = s.post(f"{BASE}/api/unsave-grant", json={"grant_id": "286103"}, headers={"X-CSRF-Token": tok2}, timeout=20)
        check("unsave_grant", r.status_code == 200, f"status={r.status_code}")
        r = s.post(f"{BASE}/api/check-eligibility", json={"grant_id": "286103", "user_info": {"organization_type": "nonprofit"}}, headers={"X-CSRF-Token": tok2}, timeout=20)
        check("check_eligibility", r.status_code == 200, f"status={r.status_code}")

        # Route aliases
        for path, expected in [
            ("/research", 302),
            ("/templates", 200),
            ("/list-templates", 200),
            ("/subscription/success", 302),
            ("/subscription/cancel", 302),
        ]:
            r = s.get(f"{BASE}{path}", timeout=20, allow_redirects=False)
            check(path, r.status_code == expected, f"status={r.status_code} loc={r.headers.get('Location','')}")

    except Exception as e:
        check("exception", False, repr(e))

    for res in results:
        status = "PASS" if res.ok else "FAIL"
        print(f"{status} {res.name}: {res.detail}")

    failed = [r for r in results if not r.ok]
    print(f"\nSummary: {len(results)-len(failed)}/{len(results)} passed")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
