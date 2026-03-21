# GrantPro Background Jobs

## sync_grants_gov.py

Daily sync of federal grant opportunities from the Grants.gov public API into the local `grants_catalog` SQLite table.

### What it does

1. Ensures the database and `grants_catalog` table exist (calls `init_db()` and `seed_grants_catalog()`).
2. Fetches opportunities from `https://api.grants.gov/v1/api/search` with pagination.
3. Maps each opportunity to the `grants_catalog` schema and upserts (INSERT OR REPLACE).
4. Archives grants whose `close_date` has passed, unless they are referenced by an active user application.
5. Logs results to `tracking/sync.log`.

### Usage

```bash
# Run manually
python3 jobs/sync_grants_gov.py

# With options
python3 jobs/sync_grants_gov.py --keyword energy --max-results 100
```

### Scheduling with cron

```cron
# Run daily at 4 AM
0 4 * * * cd /path/to/grant-system && python3 jobs/sync_grants_gov.py >> tracking/sync.log 2>&1
```

### Dependencies

- `requests` (Python package)
- SQLite3 (standard library)
- The `core/grant_db.py` module (for `init_db` and `seed_grants_catalog`)

---

## check_awards.py

Detects grant award winners by cross-referencing USAspending.gov federal award data against GrantPro clients and users. When a match is found, it creates an `award_matches` record and sends a congratulations email with a unique link to the testimonial form.

### What it does

1. Loads all organization names from the `clients` and `users` tables.
2. Queries the USAspending.gov spending-by-award API for recent grant awards (last 30 days).
3. For each award, performs case-insensitive LIKE matching of the recipient name against known organizations.
4. On match: inserts an `award_matches` row with a unique `testimonial_token` (secrets.token_urlsafe(32)).
5. Sends a congratulations email via `core/email_system.py` containing a link to `/testimonial/<token>`.
6. If Resend is not configured, logs the email details to the console.
7. Logs all activity to `tracking/check_awards.log`.

### Usage

```bash
# Run manually
python3 jobs/check_awards.py
```

### Scheduling with cron

```cron
# Run weekly on Mondays at 6 AM
0 6 * * 1 cd /path/to/grant-system && python3 jobs/check_awards.py >> tracking/check_awards.log 2>&1
```

### Dependencies

- `requests` (Python package)
- SQLite3 (standard library)
- `core/grant_db.py` (for `init_db`)
- `core/email_system.py` (for `send_award_congratulations`)
