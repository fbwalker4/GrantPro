#!/usr/bin/env python3
"""
Grant Writing System - User Models
Handles user authentication and user data
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime
from pathlib import Path

from db_connection import LOCAL_DB_PATH as DB_PATH
from db_connection import get_connection

# Column order must match the CREATE TABLE + ALTER TABLE schema exactly
USER_COLUMNS = [
    'id', 'email', 'password_hash', 'first_name', 'last_name',
    'organization_name', 'organization_type', 'phone', 'role',
    'verified', 'verification_token', 'created_at', 'updated_at',
    'last_login', 'plan', 'grants_this_month', 'max_grants_per_month',
    'subscription_status', 'stripe_customer_id', 'stripe_subscription_id',
    'subscription_start', 'subscription_end', 'onboarding_completed',
    'payment_failure_count', 'first_payment_failure_at', 'suspended_at',
    'data_deletion_eligible_at', 'cancellation_effective_at', 'last_dunning_email_at',
    'renewal_reminder_sent', 'pause_started_at', 'pause_ends_at',
    'pause_count_this_year', 'cancellation_reason', 'deleted_at', 'plan_before_suspension'
]

def init_user_db():
    """Initialize user-related database tables.

    On Postgres (Supabase) the schema is applied via supabase_migration.sql,
    so CREATE TABLE / ALTER TABLE may fail with 'already exists'.  We wrap
    the entire block in try/except so the app starts cleanly either way.
    """
    conn = get_connection()
    c = conn.cursor()

    try:
        # Users table - expanded for subscriptions
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            organization_name TEXT,
            organization_type TEXT,
            phone TEXT,
            role TEXT DEFAULT 'user',
            plan TEXT DEFAULT 'free',
            grants_this_month INTEGER DEFAULT 0,
            max_grants_per_month INTEGER DEFAULT 0,
            subscription_status TEXT DEFAULT 'inactive',
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            subscription_start TEXT,
            subscription_end TEXT,
            created_at TEXT,
            updated_at TEXT,
            last_login TEXT
        )''')

        # User profiles (additional info)
        c.execute('''CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            bio TEXT,
            interests TEXT,
            eligible_entities TEXT,
            funding_amount_min INTEGER,
            funding_amount_max INTEGER,
            preferred_categories TEXT,
            notify_deadlines INTEGER DEFAULT 1,
            notify_new_grants INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')

        # Saved grants (favorites)
        c.execute('''CREATE TABLE IF NOT EXISTS saved_grants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            grant_id TEXT NOT NULL,
            notes TEXT,
            saved_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, grant_id)
        )''')

        # User applications (tracking)
        c.execute('''CREATE TABLE IF NOT EXISTS user_applications (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            grant_id TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            progress INTEGER DEFAULT 0,
            started_at TEXT,
            updated_at TEXT,
            submitted_at TEXT,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')

        # Password reset tokens
        c.execute('''CREATE TABLE IF NOT EXISTS password_resets (
            email TEXT NOT NULL,
            token TEXT NOT NULL,
            created_at TEXT,
            expires_at TEXT,
            used INTEGER DEFAULT 0
        )''')

        # Organization details - federal identifiers and contact info
        c.execute('''CREATE TABLE IF NOT EXISTS organization_details (
            user_id TEXT PRIMARY KEY,
            ein TEXT,
            duns TEXT,
            uei TEXT,
            address_line1 TEXT,
            address_line2 TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            country TEXT DEFAULT 'USA',
            phone TEXT,
            website TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')

        # Organization profile - size and history
        c.execute('''CREATE TABLE IF NOT EXISTS organization_profile (
            user_id TEXT PRIMARY KEY,
            annual_revenue TEXT,
            year_founded INTEGER,
            employees TEXT,
            organization_type TEXT,
            mission_statement TEXT,
            programs_description TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')

        # Migrate existing tables: add mission_statement and programs_description if missing
        try:
            c.execute('ALTER TABLE organization_profile ADD COLUMN mission_statement TEXT')
        except Exception:
            pass
        try:
            c.execute('ALTER TABLE organization_profile ADD COLUMN programs_description TEXT')
        except Exception:
            pass

        # Mission and focus areas - who do you serve
        c.execute('''CREATE TABLE IF NOT EXISTS mission_focus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            focus_area TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, focus_area)
        )''')

        # Past grant experience
        c.execute('''CREATE TABLE IF NOT EXISTS past_grant_experience (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            grant_name TEXT,
            funding_organization TEXT,
            year_received INTEGER,
            amount_received INTEGER,
            status TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')

        # Track if user has completed onboarding
        try:
            c.execute('''ALTER TABLE users ADD COLUMN onboarding_completed INTEGER DEFAULT 0''')
        except Exception:
            pass  # Column already exists (Postgres or repeated SQLite run)

        # Subscription lifecycle columns
        for col, default in [
            ('payment_failure_count', 'INTEGER DEFAULT 0'),
            ('first_payment_failure_at', 'TEXT'),
            ('suspended_at', 'TEXT'),
            ('data_deletion_eligible_at', 'TEXT'),
            ('cancellation_effective_at', 'TEXT'),
            ('last_dunning_email_at', 'TEXT'),
            ('renewal_reminder_sent', 'INTEGER DEFAULT 0'),
            ('pause_started_at', 'TEXT'),
            ('pause_ends_at', 'TEXT'),
            ('pause_count_this_year', 'INTEGER DEFAULT 0'),
            ('cancellation_reason', 'TEXT'),
            ('deleted_at', 'TEXT'),
            ('plan_before_suspension', 'TEXT'),
        ]:
            try:
                c.execute(f'ALTER TABLE users ADD COLUMN {col} {default}')
            except Exception:
                pass

        # Subscription events audit trail
        c.execute('''CREATE TABLE IF NOT EXISTS subscription_events (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            stripe_event_id TEXT,
            metadata TEXT,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')

        # Data exports
        c.execute('''CREATE TABLE IF NOT EXISTS data_exports (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            file_path TEXT,
            file_size INTEGER,
            requested_at TEXT,
            completed_at TEXT,
            expires_at TEXT,
            download_count INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )''')

        # Account deletion tombstones
        c.execute('''CREATE TABLE IF NOT EXISTS account_deletions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            email TEXT NOT NULL,
            plan_at_deletion TEXT,
            deletion_reason TEXT,
            initiated_by TEXT DEFAULT 'user',
            tables_purged TEXT,
            created_at TEXT
        )''')
    except Exception as e:
        # On Postgres the schema is managed by supabase_migration.sql
        # so failures here (e.g. AUTOINCREMENT syntax) are expected.
        import logging
        logging.getLogger(__name__).info("init_user_db migration note (expected on Postgres): %s", e)

    try:
        conn.commit()
    except Exception:
        pass
    conn.close()
    return True


def hash_password(password):
    """Hash a password using PBKDF2 with high iterations"""
    salt = secrets.token_hex(32)
    # Use PBKDF2 with 100000 iterations - much more secure than SHA-256
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return f"{salt}${pwd_hash}"


def verify_password(password, stored):
    """Verify a password against stored hash (constant-time comparison)"""
    import hmac as _hmac
    try:
        salt, pwd_hash = stored.split('$')
        verify_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        return _hmac.compare_digest(verify_hash, pwd_hash)
    except (ValueError, AttributeError, TypeError):
        return False


def create_user(email, password, first_name=None, last_name=None, organization_name=None, plan='free'):
    """Create a new user"""
    conn = get_connection()
    c = conn.cursor()
    
    # Check if email exists
    c.execute('SELECT id FROM users WHERE email = ?', (email,))
    if c.fetchone():
        conn.close()
        return None, "Email already registered"
    
    user_id = f"user-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(4)}"
    now = datetime.now().isoformat()
    password_hash=hash_password(password)
    
    # Set limits based on plan
    plan_limits = {
        'free': (0, 0),                    # Free: search only, no grants
        'monthly': (3, 19.95),            # Monthly: 3 grants, $19.95/mo
        'annual': (3, 199),               # Annual: 3 grants, $199/yr
        'enterprise_5': (999, 44.95),     # Enterprise 5: unlimited grants, 5 clients
        'enterprise_10': (999, 74.95),    # Enterprise 10: unlimited grants, 10 clients
        'enterprise_unlimited': (999, 99.95),  # Enterprise Unlimited: unlimited everything
    }
    
    max_grants = plan_limits.get(plan, (0, 0))[0]
    
    try:
        c.execute('''INSERT INTO users (id, email, password_hash, first_name, last_name, organization_name, role, plan, grants_this_month, max_grants_per_month, subscription_status, created_at, updated_at)
                     VALUES (?, ?, ?, ?, ?, ?, 'user', ?, 0, ?, 'inactive', ?, ?)''',
                  (user_id, email, password_hash, first_name, last_name, organization_name, plan, max_grants, now, now))
        
        # Create empty profile
        c.execute('INSERT INTO user_profiles (user_id) VALUES (?)', (user_id,))
        
        conn.commit()
        conn.close()
        return user_id, None
    except Exception as e:
        conn.close()
        return None, str(e)


def get_user_by_email(email):
    """Get user by email"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (email,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return dict(row) if hasattr(row, 'keys') else dict(zip(USER_COLUMNS, row))
    return None


def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()

    if row:
        return dict(row) if hasattr(row, 'keys') else dict(zip(USER_COLUMNS, row))
    return None


def update_user_plan(user_id, plan, stripe_customer_id=None, stripe_subscription_id=None):
    """Update user's subscription plan"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    # Set limits based on plan
    plan_limits = {
        'free': (0, 'inactive'),                    # Free: search only, no grants
        'monthly': (3, 'active'),                   # Monthly: 3 grants/mo, $19.95
        'annual': (3, 'active'),                    # Annual: 3 grants/mo, $199/yr
        'enterprise_5': (999, 'active'),            # Enterprise 5: unlimited, 5 clients
        'enterprise_10': (999, 'active'),           # Enterprise 10: unlimited, 10 clients
        'enterprise_unlimited': (999, 'active'),    # Enterprise Unlimited
    }
    
    max_grants, sub_status = plan_limits.get(plan, (0, 'inactive'))
    
    # Build update query
    if stripe_customer_id and stripe_subscription_id:
        c.execute('''UPDATE users SET plan = ?, max_grants_per_month = ?, subscription_status = ?, 
                      stripe_customer_id = ?, stripe_subscription_id = ?, updated_at = ? WHERE id = ?''', 
                  (plan, max_grants, sub_status, stripe_customer_id, stripe_subscription_id, now, user_id))
    else:
        c.execute('UPDATE users SET plan = ?, max_grants_per_month = ?, subscription_status = ?, updated_at = ? WHERE id = ?', 
                  (plan, max_grants, sub_status, now, user_id))
    conn.commit()
    conn.close()
    
    return True


def get_user_profile(user_id):
    """Get user profile"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM user_profiles WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        # Use column names from cursor description for forward compatibility
        return dict(row) if hasattr(row, 'keys') else dict(zip([desc[0] for desc in c.description], row))
    return None


def update_user_profile(user_id, profile_data):
    """Update user profile"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    # Build update query with safe field validation
    allowed_fields = {
        'bio', 'interests', 'eligible_entities', 'funding_amount_min',
        'funding_amount_max', 'preferred_categories', 'notify_deadlines',
        'notify_new_grants', 'reminder_days', 'first_name', 'last_name',
        'organization_name', 'organization_type'
    }
    
    fields = []
    values = []
    for key, value in profile_data.items():
        if key in allowed_fields:
            fields.append(f"{key} = ?")
            values.append(value)
    
    if not fields:
        conn.close()
        return
    
    values.append(user_id)
    
    # Use parameterized query - join safely since we validated field names
    query = f'UPDATE user_profiles SET {", ".join(fields)} WHERE user_id = ?'
    c.execute(query, values)
    
    # Also update users table if needed
    if 'first_name' in profile_data:
        c.execute('UPDATE users SET first_name = ?, updated_at = ? WHERE id = ?', (profile_data['first_name'], now, user_id))
    if 'last_name' in profile_data:
        c.execute('UPDATE users SET last_name = ?, updated_at = ? WHERE id = ?', (profile_data['last_name'], now, user_id))
    if 'organization_name' in profile_data:
        c.execute('UPDATE users SET organization_name = ?, updated_at = ? WHERE id = ?', (profile_data['organization_name'], now, user_id))
    if 'organization_type' in profile_data:
        c.execute('UPDATE users SET organization_type = ?, updated_at = ? WHERE id = ?', (profile_data['organization_type'], now, user_id))
    
    conn.commit()
    conn.close()


def save_grant(user_id, grant_id, notes=None):
    """Save a grant to user's favorites"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    try:
        c.execute('INSERT OR REPLACE INTO saved_grants (user_id, grant_id, notes, saved_at) VALUES (?, ?, ?, ?)',
                  (user_id, grant_id, notes, now))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False


def unsave_grant(user_id, grant_id):
    """Remove a grant from favorites"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM saved_grants WHERE user_id = ? AND grant_id = ?', (user_id, grant_id))
    conn.commit()
    conn.close()


def get_saved_grants(user_id):
    """Get all saved grants for a user"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''SELECT s.grant_id, s.notes, s.saved_at 
                 FROM saved_grants s 
                 WHERE s.user_id = ? 
                 ORDER BY s.saved_at DESC''', (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) if hasattr(row, 'keys') else dict(zip(['grant_id', 'notes', 'saved_at'], row)) for row in rows]


def get_user_grants(user_id):
    """Get all applications/grants for a user"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''SELECT a.id, a.grant_id, a.status, a.progress, a.started_at, a.updated_at, a.submitted_at, a.notes
                 FROM user_applications a 
                 WHERE a.user_id = ? 
                 ORDER BY a.updated_at DESC''', (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) if hasattr(row, 'keys') else dict(zip(['id', 'grant_id', 'status', 'progress', 'started_at', 'updated_at', 'submitted_at', 'notes'], row)) for row in rows]


def get_user_clients(user_id):
    """Get list of client IDs for a user"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM clients WHERE user_id = ?', (user_id,))
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_all_clients():
    """Get all clients"""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM clients ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def is_grant_saved(user_id, grant_id):
    """Check if a grant is saved by user"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM saved_grants WHERE user_id = ? AND grant_id = ?', (user_id, grant_id))
    row = c.fetchone()
    conn.close()
    return row is not None


def create_password_reset(email):
    """Create password reset token"""
    conn = get_connection()
    c = conn.cursor()
    
    # Check if user exists
    c.execute('SELECT id FROM users WHERE email = ?', (email,))
    if not c.fetchone():
        conn.close()
        return False
    
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    # Fix: use timedelta instead of replacing hour which can exceed 23
    from datetime import timedelta
    expires = now + timedelta(hours=24)
    
    c.execute('INSERT OR REPLACE INTO password_resets (email, token, created_at, expires_at) VALUES (?, ?, ?, ?)',
              (email, token, now.isoformat(), expires.isoformat()))
    conn.commit()
    conn.close()
    
    # In production, send email here
    return token


def verify_password_reset(token):
    """Verify and use password reset token"""
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('SELECT email, expires_at, used FROM password_resets WHERE token = ?', (token,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return None, "Invalid token"
    
    email, expires_at, used = row
    
    if used:
        conn.close()
        return None, "Token already used"
    
    if datetime.now() > datetime.fromisoformat(expires_at):
        conn.close()
        return None, "Token expired"
    
    conn.close()
    return email, None


def use_password_reset(token, new_password):
    """Complete password reset — atomic verify + use to prevent TOCTOU race."""
    conn = get_connection()
    c = conn.cursor()

    # Verify and mark used in a single transaction
    c.execute('SELECT email, expires_at, used FROM password_resets WHERE token = ?', (token,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, "Invalid or expired reset link"

    email = row['email'] if isinstance(row, dict) else row[0]
    expires_at = row['expires_at'] if isinstance(row, dict) else row[1]
    used = row['used'] if isinstance(row, dict) else row[2]

    if used:
        conn.close()
        return False, "This reset link has already been used"
    if datetime.now() > datetime.fromisoformat(str(expires_at)):
        conn.close()
        return False, "This reset link has expired"

    password_hash = hash_password(new_password)
    c.execute('UPDATE users SET password_hash = ?, updated_at = ? WHERE email = ?',
              (password_hash, datetime.now().isoformat(), email))
    c.execute('UPDATE password_resets SET used = 1 WHERE token = ?', (token,))

    conn.commit()
    conn.close()
    return True, None


def update_last_login(user_id):
    """Update user's last login time"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()


def update_user(user_id, user_data):
    """Update user record"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    # Allowed fields for users table
    allowed_fields = {'first_name', 'last_name', 'organization_name', 'organization_type', 'phone'}
    
    fields = []
    values = []
    for key, value in user_data.items():
        if key in allowed_fields:
            fields.append(f"{key} = ?")
            values.append(value)
    
    if not fields:
        conn.close()
        return
    
    fields.append('updated_at = ?')
    values.append(now)
    values.append(user_id)
    
    query = f'UPDATE users SET {", ".join(fields)} WHERE id = ?'
    c.execute(query, values)
    
    conn.commit()
    conn.close()


def check_grant_limit(user_id):
    """Check if user can create more grants. Returns (can_create: bool, message: str, remaining: int)"""
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('SELECT grants_this_month, max_grants_per_month, plan, subscription_status FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return False, "User not found", 0
    
    used, max_allowed, plan, sub_status = row
    
    # Free users can't create grants - they can only search
    if plan == 'free' or max_allowed == 0:
        return False, "Upgrade to submit grant applications. Free tier is for research only.", 0
    
    # Enterprise plans = unlimited grants
    if plan in ('enterprise_5', 'enterprise_10', 'enterprise_unlimited'):
        return True, "Unlimited grants", 999
    
    remaining = max_allowed - used
    
    if remaining > 0:
        return True, f"{remaining} grants remaining this month", remaining
    else:
        return False, f"Monthly limit reached ({max_allowed}/month). Upgrade to submit more grants.", 0


def increment_grant_count(user_id):
    """Increment the user's grant count for this month"""
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('UPDATE users SET grants_this_month = grants_this_month + 1 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()


def reset_monthly_grants():
    """Reset grant counts for all users at the start of a new month - run via cron"""
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('UPDATE users SET grants_this_month = 0')
    affected = c.rowcount
    conn.commit()
    conn.close()
    
    return f"Reset grant counts for {affected} users"


def get_user_plan(user_id):
    """Get user's plan and limits"""
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('SELECT plan, grants_this_month, max_grants_per_month FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return {
        'plan': row[0],
        'used': row[1],
        'max': row[2]
    }


def get_client_limit(plan):
    """Return the maximum number of total organizations allowed for a plan.
    This includes their own primary org. Enterprise 5 = 5 total orgs.
    Returns: 0 for free, 1 for monthly/annual, 5/10/None for enterprise tiers.
    None means unlimited."""
    limits = {
        'free': 0,
        'monthly': 1,
        'annual': 1,
        'enterprise_5': 5,
        'enterprise_10': 10,
        'enterprise_unlimited': None,  # Unlimited
    }
    return limits.get(plan, 0)


def log_subscription_event(user_id, event_type, stripe_event_id=None, metadata=None):
    """Insert a row into the subscription_events audit trail."""
    import json as _json
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now()
    event_id = f"sub_event-{now.strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(8)}"
    meta_str = _json.dumps(metadata) if metadata else None
    c.execute('''INSERT INTO subscription_events (id, user_id, event_type, stripe_event_id, metadata, created_at)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (event_id, user_id, event_type, stripe_event_id, meta_str, now.isoformat()))
    conn.commit()
    conn.close()
    return event_id


def purge_user_data(user_id):
    """Permanently delete all data for a user across all tables.

    Returns list of (table_name, rows_deleted) tuples.

    Order matters: delete from child tables first to avoid FK violations.
    """
    conn = get_connection()
    c = conn.cursor()
    purged = []

    try:
        # Get user's client IDs first (needed for cascading)
        c.execute('SELECT id FROM clients WHERE user_id = ?', (user_id,))
        client_ids = [row[0] if not hasattr(row, 'keys') else row['id'] for row in c.fetchall()]

        # 1. Delete grant-linked child tables
        for cid in client_ids:
            c.execute('SELECT id FROM grants WHERE client_id = ?', (cid,))
            grant_ids = [row[0] if not hasattr(row, 'keys') else row['id'] for row in c.fetchall()]
            for gid in grant_ids:
                c.execute('DELETE FROM drafts WHERE grant_id = ?', (gid,))
                purged.append(('drafts', c.rowcount))
                c.execute('DELETE FROM grant_budget WHERE grant_id = ?', (gid,))
                purged.append(('grant_budget', c.rowcount))
                c.execute('DELETE FROM grant_shares WHERE grant_id = ?', (gid,))
                purged.append(('grant_shares', c.rowcount))
                try:
                    c.execute('DELETE FROM grant_checklist WHERE grant_id = ?', (gid,))
                    purged.append(('grant_checklist', c.rowcount))
                except Exception:
                    pass
                try:
                    c.execute('DELETE FROM grant_documents WHERE grant_id = ?', (gid,))
                    purged.append(('grant_documents', c.rowcount))
                except Exception:
                    pass

        # 2. Delete grants and other client-linked tables
        for cid in client_ids:
            c.execute('DELETE FROM grants WHERE client_id = ?', (cid,))
            purged.append(('grants', c.rowcount))
            c.execute('DELETE FROM documents WHERE client_id = ?', (cid,))
            purged.append(('documents', c.rowcount))
            c.execute('DELETE FROM invoices WHERE client_id = ?', (cid,))
            purged.append(('invoices', c.rowcount))

        # 3. Delete clients
        c.execute('DELETE FROM clients WHERE user_id = ?', (user_id,))
        purged.append(('clients', c.rowcount))

        # 4. Delete user-linked tables
        for table in [
            'saved_grants', 'user_applications', 'user_profiles',
            'organization_details', 'organization_profile', 'mission_focus',
            'past_grant_experience', 'subscription_events', 'data_exports',
            'award_matches', 'testimonials',
        ]:
            try:
                c.execute(f'DELETE FROM {table} WHERE user_id = ?', (user_id,))
                purged.append((table, c.rowcount))
            except Exception:
                pass

        # 5. Delete from tables keyed by email
        c.execute('SELECT email FROM users WHERE id = ?', (user_id,))
        row = c.fetchone()
        if row:
            email = row[0] if not hasattr(row, 'keys') else row['email']
            for table in ['password_resets', 'leads', 'guest_saves']:
                try:
                    c.execute(f'DELETE FROM {table} WHERE email = ?', (email,))
                    purged.append((table, c.rowcount))
                except Exception:
                    pass
            try:
                c.execute('DELETE FROM email_log WHERE to_email = ?', (email,))
                purged.append(('email_log', c.rowcount))
            except Exception:
                pass

        # 6. Vault documents
        try:
            c.execute('DELETE FROM org_vault WHERE user_id = ?', (user_id,))
            purged.append(('org_vault', c.rowcount))
        except Exception:
            pass

        # 7. Grant readiness
        try:
            c.execute('DELETE FROM grant_readiness WHERE user_id = ?', (user_id,))
            purged.append(('grant_readiness', c.rowcount))
        except Exception:
            pass

        # 8. Finally, delete the user
        c.execute('DELETE FROM users WHERE id = ?', (user_id,))
        purged.append(('users', c.rowcount))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

    return purged


def record_account_deletion(user_id, email, plan, reason='user_requested', initiated_by='user', tables_purged=None):
    """Record a tombstone after account deletion for compliance."""
    import json as _json
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now()
    deletion_id = f"del-{now.strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"

    c.execute('''INSERT INTO account_deletions (id, user_id, email, plan_at_deletion, deletion_reason, initiated_by, tables_purged, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
             (deletion_id, user_id, email, plan, reason, initiated_by,
              _json.dumps(tables_purged) if tables_purged else None, now.isoformat()))
    conn.commit()
    conn.close()
    return deletion_id


def soft_delete_user(user_id):
    """Mark user for deletion (72-hour grace period before purge)."""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now()
    c.execute('''UPDATE users SET
                  subscription_status = 'pending_deletion',
                  deleted_at = ?,
                  updated_at = ?
                  WHERE id = ?''', (now.isoformat(), now.isoformat(), user_id))
    conn.commit()
    conn.close()

    log_subscription_event(user_id, 'deletion_requested')
    return True


def cancel_deletion(user_id):
    """Cancel a pending deletion within the 72-hour grace period."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT deleted_at, plan FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, "No pending deletion"

    deleted_at_val = row[0] if not hasattr(row, 'keys') else row['deleted_at']
    plan = row[1] if not hasattr(row, 'keys') else row['plan']

    if not deleted_at_val:
        conn.close()
        return False, "No pending deletion"

    deleted_at = datetime.fromisoformat(deleted_at_val)
    if (datetime.now() - deleted_at).total_seconds() > 72 * 3600:
        conn.close()
        return False, "Grace period has expired"

    # Restore to previous status
    new_status = 'active' if plan != 'free' else 'inactive'

    c.execute('''UPDATE users SET
                  subscription_status = ?,
                  deleted_at = NULL,
                  updated_at = ?
                  WHERE id = ?''', (new_status, datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

    log_subscription_event(user_id, 'deletion_cancelled')
    return True, "Deletion cancelled"


if __name__ == '__main__':
    init_user_db()
    print("User database initialized")


# ============ ORGANIZATION ONBOARDING FUNCTIONS ============

def get_organization_details(user_id):
    """Get all organization details for a user"""
    conn = get_connection()
    c = conn.cursor()
    
    # Get organization details
    c.execute('SELECT * FROM organization_details WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    
    org_details = None
    if row:
        org_details = dict(row) if hasattr(row, 'keys') else dict(zip(['user_id', 'ein', 'duns', 'uei', 'address_line1', 'address_line2',
                               'city', 'state', 'zip_code', 'country', 'phone', 'website',
                               'created_at', 'updated_at'], row))
    
    # Get organization profile
    c.execute('SELECT * FROM organization_profile WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    
    org_profile = None
    if row:
        cols = ['user_id', 'annual_revenue', 'year_founded', 'employees', 'organization_type',
                'mission_statement', 'programs_description']
        org_profile = dict(row) if hasattr(row, 'keys') else dict(zip(cols[:len(row)], row))
    
    # Get focus areas
    c.execute('SELECT focus_area FROM mission_focus WHERE user_id = ?', (user_id,))
    focus_rows = c.fetchall()
    focus_areas = [row['focus_area'] if hasattr(row, 'keys') else row[0] for row in focus_rows]
    
    # Get past grant experience
    c.execute('SELECT id, grant_name, funding_organization, year_received, amount_received, status FROM past_grant_experience WHERE user_id = ?', (user_id,))
    past_grants = []
    for row in c.fetchall():
        past_grants.append({
            'id': row[0],
            'grant_name': row[1],
            'funding_organization': row[2],
            'year_received': row[3],
            'amount_received': row[4],
            'status': row[5]
        })
    
    # Get onboarding status
    c.execute('SELECT onboarding_completed FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    onboarding_completed = row[0] if row else 0
    
    conn.close()
    
    return {
        'organization_details': org_details,
        'organization_profile': org_profile,
        'focus_areas': focus_areas,
        'past_grants': past_grants,
        'onboarding_completed': onboarding_completed
    }


def save_organization_details(user_id, data):
    """Save all organization details for a user"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    # Extract data
    org_details = data.get('organization_details', {})
    org_profile = data.get('organization_profile', {})
    focus_areas = data.get('focus_areas', [])
    past_grants = data.get('past_grants', [])
    
    # Save organization details
    c.execute('''INSERT OR REPLACE INTO organization_details 
                 (user_id, ein, duns, uei, address_line1, address_line2, city, state, zip_code, country, phone, website, created_at, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
               (user_id, 
                org_details.get('ein'), org_details.get('duns'), org_details.get('uei'),
                org_details.get('address_line1'), org_details.get('address_line2'),
                org_details.get('city'), org_details.get('state'), org_details.get('zip_code'),
                org_details.get('country', 'USA'), org_details.get('phone'), org_details.get('website'),
                now, now))
    
    # Save organization profile
    c.execute('''INSERT OR REPLACE INTO organization_profile
                 (user_id, annual_revenue, year_founded, employees, organization_type,
                  mission_statement, programs_description)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
               (user_id,
                org_profile.get('annual_revenue'), org_profile.get('year_founded'),
                org_profile.get('employees'), org_profile.get('organization_type'),
                org_profile.get('mission_statement'), org_profile.get('programs_description')))
    
    # Clear and re-insert focus areas
    c.execute('DELETE FROM mission_focus WHERE user_id = ?', (user_id,))
    for area in focus_areas:
        if area.strip():
            c.execute('INSERT INTO mission_focus (user_id, focus_area) VALUES (?, ?)', (user_id, area.strip()))
    
    # Clear and re-insert past grants
    c.execute('DELETE FROM past_grant_experience WHERE user_id = ?', (user_id,))
    for grant in past_grants:
        if grant.get('grant_name'):
            c.execute('''INSERT INTO past_grant_experience 
                         (user_id, grant_name, funding_organization, year_received, amount_received, status)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                     (user_id, grant.get('grant_name'), grant.get('funding_organization'),
                      grant.get('year_received'), grant.get('amount_received'), grant.get('status')))
    
    # Mark onboarding as completed
    c.execute('UPDATE users SET onboarding_completed = 1, updated_at = ? WHERE id = ?', (now, user_id))
    
    conn.commit()
    conn.close()
    
    return True


def is_onboarding_complete(user_id):
    """Check if user has completed onboarding"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT onboarding_completed FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] == 1 if row else False


# ============ GRANT READINESS PROFILE ============

GRANT_READINESS_COLUMNS = [
    'user_id', 'applicant_category', 'is_501c3', 'is_government',
    'government_type', 'is_pha', 'is_chdo', 'is_university',
    'is_small_business', 'employee_count', 'sam_gov_status',
    'sam_gov_expiry', 'has_uei', 'has_grants_gov', 'has_indirect_rate',
    'indirect_rate_type', 'indirect_rate_pct', 'cognizant_agency',
    'had_single_audit', 'annual_federal_funding', 'largest_federal_grant',
    'has_construction_experience', 'has_grants_administrator',
    'funding_purposes', 'funding_range_min', 'funding_range_max',
    'created_at', 'updated_at'
]


def get_grant_readiness(user_id):
    """Get grant readiness profile for a user"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM grant_readiness WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()

    if row:
        return dict(row) if hasattr(row, 'keys') else dict(zip(GRANT_READINESS_COLUMNS, row))
    return {}


def save_grant_readiness(user_id, data):
    """Save or update grant readiness profile for a user"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()

    # Check if record exists
    c.execute('SELECT user_id FROM grant_readiness WHERE user_id = ?', (user_id,))
    exists = c.fetchone()

    # Parse boolean values from form data
    def to_bool(val):
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ('true', '1', 'yes', 'on')
        return bool(val)

    def to_int(val, default=0):
        try:
            return int(val) if val else default
        except (ValueError, TypeError):
            return default

    def to_float(val, default=None):
        try:
            return float(val) if val else default
        except (ValueError, TypeError):
            return default

    params = {
        'applicant_category': data.get('applicant_category', ''),
        'is_501c3': to_bool(data.get('is_501c3')),
        'is_government': to_bool(data.get('is_government')),
        'government_type': data.get('government_type', ''),
        'is_pha': to_bool(data.get('is_pha')),
        'is_chdo': to_bool(data.get('is_chdo')),
        'is_university': to_bool(data.get('is_university')),
        'is_small_business': to_bool(data.get('is_small_business')),
        'employee_count': to_int(data.get('employee_count')),
        'sam_gov_status': data.get('sam_gov_status', 'unknown'),
        'sam_gov_expiry': data.get('sam_gov_expiry', ''),
        'has_uei': to_bool(data.get('has_uei')),
        'has_grants_gov': to_bool(data.get('has_grants_gov')),
        'has_indirect_rate': to_bool(data.get('has_indirect_rate')),
        'indirect_rate_type': data.get('indirect_rate_type', ''),
        'indirect_rate_pct': to_float(data.get('indirect_rate_pct')),
        'cognizant_agency': data.get('cognizant_agency', ''),
        'had_single_audit': to_bool(data.get('had_single_audit')),
        'annual_federal_funding': to_int(data.get('annual_federal_funding')),
        'largest_federal_grant': to_int(data.get('largest_federal_grant')),
        'has_construction_experience': to_bool(data.get('has_construction_experience')),
        'has_grants_administrator': to_bool(data.get('has_grants_administrator')),
        'funding_purposes': data.get('funding_purposes', ''),
        'funding_range_min': to_int(data.get('funding_range_min')),
        'funding_range_max': to_int(data.get('funding_range_max')),
    }

    if exists:
        set_clause = ', '.join(f"{k} = ?" for k in params.keys())
        values = list(params.values()) + [now, user_id]
        c.execute(f'UPDATE grant_readiness SET {set_clause}, updated_at = ? WHERE user_id = ?', values)
    else:
        cols = ['user_id'] + list(params.keys()) + ['created_at', 'updated_at']
        placeholders = ', '.join(['?'] * len(cols))
        values = [user_id] + list(params.values()) + [now, now]
        c.execute(f'INSERT INTO grant_readiness ({", ".join(cols)}) VALUES ({placeholders})', values)

    conn.commit()
    conn.close()
    return True


def get_readiness_completion(readiness):
    """Calculate grant readiness completion score.
    Returns (percentage, list_of_missing_labels).
    """
    if not readiness:
        return 0, ['Applicant Type', 'SAM.gov Status', 'UEI Number', 'Grants.gov Account',
                    'Federal Funding History', 'Funding Preferences']

    fields = [
        (bool(readiness.get('applicant_category')), 'Applicant Type'),
        (readiness.get('sam_gov_status', 'unknown') != 'unknown', 'SAM.gov Status'),
        (bool(readiness.get('has_uei')), 'UEI Number'),
        (bool(readiness.get('has_grants_gov')), 'Grants.gov Account'),
        (readiness.get('largest_federal_grant', 0) > 0, 'Federal Funding History'),
        (bool(readiness.get('funding_purposes')), 'Funding Preferences'),
    ]

    filled = sum(1 for complete, _ in fields if complete)
    total = len(fields)
    pct = int(round(filled / total * 100)) if total else 0
    missing = [label for complete, label in fields if not complete]
    return pct, missing
