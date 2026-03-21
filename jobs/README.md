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
