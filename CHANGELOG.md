# Changelog

All notable changes to GrantPro are documented here.

## [Unreleased]

### Fixed

- **Agency badge truncation**: Long agency codes (e.g. `HHS-NIH11`) could be truncated to `HHS-` in grant cards due to `justify-content: space-between` without flex-wrap. Added `flex-wrap: wrap` to `.grant-card-top` so badges wrap to the next line instead of overflowing.

- **Inconsistent date formats on grant cards**: Grants.gov data had mixed date formats — some stored as `YYYY-MM-DD` (e.g. `2026-02-01`) and others as `MM/DD/YYYY` (e.g. `12/31/2024`) — causing inconsistent display (e.g. `12/31/2024` appearing alongside `2026-07-15`). Added `std_date` Jinja2 filter (`portal/app.py`) that normalizes all date values to `YYYY-MM-DD` format uniformly. Applied to both `open_date` (Posted) and `close_date`/`deadline` (Deadline) fields in the search results template.

- **Orphaned 'Grants' nav link on pricing page**: The pricing page nav had a dead `Grants` link (`/grants`) that pointed to a non-existent route. Removed the dangling link.

### Verified Working

- **Signup and login forms**: Confirmed via Browserbase E2E testing that signup and login forms submit correctly and create sessions as expected. No backend or JavaScript issues found — earlier test failures were due to non-existent test accounts.

---

*Last updated: 2026-04-09*
