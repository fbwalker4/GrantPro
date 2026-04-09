#!/usr/bin/env python3
"""
GrantPro Database Hygiene Script
- Normalizes close_date formats
- Merges 'active' status into 'posted'
- Archives expired grants (close_date in past) that haven't been saved/used in 30+ days
- Removes grants with no close_date that are >1 year old
Run weekly via Supabase pg_cron or system cron.
"""
import psycopg2, re, urllib.parse, os
from datetime import datetime, timedelta

DATABASE_URL = os.environ.get('DATABASE_URL', '') or 'postgresql://postgres.mubghncbtnkjkywbcfts:GrantPro2026%21Secure@aws-1-us-east-1.pooler.supabase.com:6543/postgres'

def parse_date(s):
    """Parse various date formats to YYYY-MM-DD"""
    if not s or str(s).strip() in ('', 'None'):
        return None
    s = str(s).strip()
    # Already ISO format
    if re.match(r'^\d{4}-\d{2}-\d{2}', s):
        return s[:10]
    # MM/DD/YYYY
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', s)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    # DD/MM/YYYY
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', s)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return None

def run_hygiene():
    parsed = urllib.parse.urlparse(DATABASE_URL)
    conn = psycopg2.connect(
        host=parsed.hostname, port=parsed.port, dbname=parsed.path[1:],
        user=parsed.username, password=parsed.password
    )
    conn.autocommit = True
    c = conn.cursor()
    stats = {}
    
    # 1. Normalize close_date formats
    c.execute("SELECT id, close_date FROM grants_catalog WHERE close_date IS NOT NULL AND close_date != ''")
    rows = c.fetchall()
    normalized = 0
    for grant_id, close_date in rows:
        new_date = parse_date(close_date)
        if new_date and new_date != str(close_date):
            c.execute("UPDATE grants_catalog SET close_date = %s WHERE id = %s", (new_date, grant_id))
            normalized += 1
    stats['normalized_dates'] = normalized
    print(f"Normalized {normalized} close_date formats")
    
    # 2. Merge 'active' status into 'posted'
    c.execute("SELECT COUNT(*) FROM grants_catalog WHERE status = 'active'")
    active_count = c.fetchone()[0]
    c.execute("UPDATE grants_catalog SET status = 'posted' WHERE status = 'active'")
    stats['active_merged'] = active_count
    print(f"Merged {active_count} 'active' grants into 'posted'")
    
    # 3. Archive expired grants (>30 days past close_date, not saved/used)
    # First find truly expired grants (close_date < 30 days ago)
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    c.execute("""
        SELECT COUNT(*) FROM grants_catalog
        WHERE close_date IS NOT NULL AND close_date != ''
        AND CAST(close_date AS DATE) < %s
        AND status != 'archived'
        AND id NOT IN (
            SELECT DISTINCT grant_id FROM saved_grants WHERE grant_id IS NOT NULL
        )
        AND id NOT IN (
            SELECT DISTINCT grant_id FROM user_applications WHERE grant_id IS NOT NULL
        )
    """, (thirty_days_ago,))
    to_archive = c.fetchone()[0]
    c.execute("""
        UPDATE grants_catalog
        SET status = 'archived'
        WHERE close_date IS NOT NULL AND close_date != ''
        AND CAST(close_date AS DATE) < %s
        AND status != 'archived'
        AND id NOT IN (SELECT DISTINCT grant_id FROM saved_grants WHERE grant_id IS NOT NULL)
        AND id NOT IN (SELECT DISTINCT grant_id FROM user_applications WHERE grant_id IS NOT NULL)
    """, (thirty_days_ago,))
    stats['archived'] = to_archive
    print(f"Archived {to_archive} expired grants (not in use)")
    
    # 4. Remove grants with no close_date that are >1 year old (probably stale test data)
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    c.execute("""
        SELECT COUNT(*) FROM grants_catalog
        WHERE (close_date IS NULL OR close_date = '' OR close_date = 'None')
        AND created_at < %s
        AND id NOT IN (SELECT DISTINCT grant_id FROM saved_grants WHERE grant_id IS NOT NULL)
        AND id NOT IN (SELECT DISTINCT grant_id FROM user_applications WHERE grant_id IS NOT NULL)
    """, (one_year_ago,))
    to_delete = c.fetchone()[0]
    c.execute("""
        DELETE FROM grants_catalog
        WHERE (close_date IS NULL OR close_date = '' OR close_date = 'None')
        AND created_at < %s
        AND id NOT IN (SELECT DISTINCT grant_id FROM saved_grants WHERE grant_id IS NOT NULL)
        AND id NOT IN (SELECT DISTINCT grant_id FROM user_applications WHERE grant_id IS NOT NULL)
    """, (one_year_ago,))
    stats['deleted_stale'] = to_delete
    print(f"Deleted {to_delete} stale grants with no close_date")
    
    # Summary
    print("\n=== Hygiene Summary ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    conn.close()
    return stats

if __name__ == '__main__':
    run_hygiene()
