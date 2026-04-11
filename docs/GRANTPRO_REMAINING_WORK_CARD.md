# GrantPro — Things Remaining To Do (Live Card)

Last updated: 2026-04-11
Owner: Hermes
Mode: Local-only execution (no push/commit yet)

## Current Position
- Phase: Setup and control artifacts complete
- Current task: Route + link inventory
- Next task: Fix dead/mismatched route behavior
- Blockers: None currently

---

## Kanban Snapshot

### TODO
- None

### Notes
- Runtime artifacts remain in `tracking/app.log` and `data/template_requests.json` from testing.

### DOING
- None

### DONE
- Created structured repair task list
- Created this live remaining-work card
- Created local worklog tracking file
- Completed route/link inventory (`docs/ROUTE_LINK_AUDIT.md`)
- Patched route mismatches for `/list-templates`, `/subscription/success`, `/subscription/cancel` in `portal/app.py`
- Confirmed `/research` is canonical redirect-to-`/grants`
- Validated CSRF and mutating API endpoints on live local server
- Added server-side pagination to `/grants`
- Reduced `/grants` default payload from ~10.3MB to ~193KB

---

## Detailed Task Tracker

| ID | Task | Priority | Status | Evidence | Notes |
|---|---|---|---|---|---|
| R1 | Route map from app.py | P1 | DONE | `docs/ROUTE_LINK_AUDIT.md` | Route extraction completed |
| R2 | Template link map | P1 | DONE | `docs/ROUTE_LINK_AUDIT.md` | Link extraction completed |
| R3 | Dead link list + fixes | P1 | DONE | `docs/ROUTE_LINK_AUDIT.md`, `portal/app.py` | Added route aliases/fixes; remaining static asset: `/static/sample_grant_application.pdf` |
| R4 | `/research` behavior alignment | P1 | DONE | `portal/app.py`, live test results | Canonical behavior confirmed: redirect to `/grants` |
| C1 | CSRF token flow standardization | P2 | DONE | `portal/app.py`, live test results | POST endpoints now behave correctly with fresh CSRF token |
| C2 | API mutation endpoint validation | P2 | DONE | `portal/app.py`, live test results | save / unsave / eligibility / template requests validated locally |
| P1 | `/grants` baseline perf measurement | P3 | DONE | `docs/GRANTPRO_WORKLOG.md` | Baseline captured |
| P2 | `/grants` optimization changes | P3 | DONE | `portal/app.py`, `portal/templates/grants.html` | Added server-side pagination |
| P3 | Post-optimization perf verification | P3 | DONE | `docs/GRANTPRO_WORKLOG.md` | Verified payload drop to ~193KB default |
| T1 | Smoke test suite update | P4 | DONE | `scripts/grantpro_smoke_test.py` | Added runnable smoke script |
| T2 | Full regression run | P4 | DONE | `docs/GRANTPRO_WORKLOG.md` | Full regression pass completed on live local server |
| D1 | Docs reconciliation/update | P5 | DONE | `docs/comprehensive-testing-report.md`, `docs/user-testing-report.md` | Marked both reports historical and non-authoritative |
| F1 | Final retest and closeout packet | P5 | DONE | `docs/GRANTPRO_CLOSEOUT_REPORT.md` | Final smoke/regression pass completed and closeout report written |

---

## Test Evidence Ledger (append only)
- 2026-04-11: Auth and critical route sweep completed (local + prod), no core 500s in tested paths.
- 2026-04-11: API endpoints verified operational with valid CSRF token in authenticated session.
- 2026-04-11: Known route mismatches observed (`/list-templates`, `/subscription/success`, `/subscription/cancel` behavior).
- 2026-04-11: Route patch applied in `portal/app.py` for all three mismatches.
- 2026-04-11: Verified patched route existence via Flask test client (`/list-templates` -> auth redirect, `/subscription/success` -> dashboard redirect, `/subscription/cancel` -> auth redirect for anon).

---

## Change Control (local only)
- Branch: `main` (clean at start)
- Remote parity at start: `origin/main` matched local HEAD
- Commit policy for this effort: hold all changes locally until final verification complete

---

## Completion Gate
This card can be marked COMPLETE only if all are true:
- No unresolved P1 route/navigation blockers
- CSRF/API mutation flows validated and documented
- `/grants` performance optimization completed and retested
- Smoke tests passing with saved output
- Documentation reconciled and current
- Final regression rerun complete
