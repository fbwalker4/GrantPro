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

DB_PATH = Path.home() / ".hermes" / "grant-system" / "tracking" / "grants.db"

def init_user_db():
    """Initialize user-related database tables"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
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
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
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
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            raise
    
    conn.commit()
    conn.close()
    return True


def hash_password(password):
    """Hash a password using PBKDF2 with high iterations"""
    salt = secrets.token_hex(32)
    # Use PBKDF2 with 100000 iterations - much more secure than SHA-256
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return f"{salt}${pwd_hash}"


def verify_password(password, stored):
    """Verify a password against stored hash"""
    try:
        salt, pwd_hash = stored.split('$')
        verify_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        return verify_hash == pwd_hash
    except:
        return False


def create_user(email, password, first_name=None, last_name=None, organization_name=None, plan='free'):
    """Create a new user"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    # Check if email exists
    c.execute('SELECT id FROM users WHERE email = ?', (email,))
    if c.fetchone():
        conn.close()
        return None, "Email already registered"
    
    user_id = f"user-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    now = datetime.now().isoformat()
    password_hash=hash_password(password)
    
    # Set limits based on plan
    plan_limits = {
        'free': (0, 0),           # Free: search only, no grants
        'monthly': (3, 19.95),   # Monthly: 3 grants, $19.95/mo
        'annual': (3, 199),      # Annual: 3 grants, $199/yr
        'enterprise': (999, 0),   # Enterprise: unlimited, custom pricing
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
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (email,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return dict(zip(['id', 'email', 'password_hash', 'first_name', 'last_name', 'organization_name', 'organization_type', 'phone', 'role', 'verified', 'verification_token', 'created_at', 'updated_at', 'last_login', 'plan', 'grants_this_month', 'max_grants_per_month', 'onboarding_completed'], row))
    return None


def get_user_by_id(user_id):
    """Get user by ID"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return dict(zip(['id', 'email', 'password_hash', 'first_name', 'last_name', 'organization_name', 'organization_type', 'phone', 'role', 'verified', 'verification_token', 'created_at', 'updated_at', 'last_login', 'plan', 'grants_this_month', 'max_grants_per_month', 'onboarding_completed'], row))
    return None


def update_user_plan(user_id, plan, stripe_customer_id=None, stripe_subscription_id=None):
    """Update user's subscription plan"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    # Set limits based on plan
    plan_limits = {
        'free': (0, 'inactive'),           # Free: search only, no grants
        'monthly': (3, 'active'),          # Monthly: 3 grants/mo, $19.95
        'annual': (3, 'active'),           # Annual: 3 grants/mo, $199/yr
        'enterprise': (999, 'active'),     # Enterprise: unlimited
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
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('SELECT * FROM user_profiles WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return dict(zip(['user_id', 'bio', 'interests', 'eligible_entities', 'funding_amount_min', 'funding_amount_max', 'preferred_categories', 'notify_deadlines', 'notify_new_grants'], row))
    return None


def update_user_profile(user_id, profile_data):
    """Update user profile"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    # Build update query with safe field validation
    allowed_fields = {
        'bio', 'interests', 'eligible_entities', 'funding_amount_min',
        'funding_amount_max', 'preferred_categories', 'notify_deadlines',
        'notify_new_grants', 'first_name', 'last_name', 'organization_name',
        'organization_type'
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
    conn = sqlite3.connect(str(DB_PATH))
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
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('DELETE FROM saved_grants WHERE user_id = ? AND grant_id = ?', (user_id, grant_id))
    conn.commit()
    conn.close()


def get_saved_grants(user_id):
    """Get all saved grants for a user"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''SELECT s.grant_id, s.notes, s.saved_at 
                 FROM saved_grants s 
                 WHERE s.user_id = ? 
                 ORDER BY s.saved_at DESC''', (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(zip(['grant_id', 'notes', 'saved_at'], row)) for row in rows]


def get_user_grants(user_id):
    """Get all applications/grants for a user"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''SELECT a.id, a.grant_id, a.status, a.progress, a.started_at, a.updated_at, a.submitted_at, a.notes
                 FROM user_applications a 
                 WHERE a.user_id = ? 
                 ORDER BY a.updated_at DESC''', (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(zip(['id', 'grant_id', 'status', 'progress', 'started_at', 'updated_at', 'submitted_at', 'notes'], row)) for row in rows]


def get_user_clients(user_id):
    """Get list of client IDs for a user"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('SELECT id FROM clients WHERE user_id = ?', (user_id,))
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_all_clients():
    """Get all clients"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM clients ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def is_grant_saved(user_id, grant_id):
    """Check if a grant is saved by user"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('SELECT id FROM saved_grants WHERE user_id = ? AND grant_id = ?', (user_id, grant_id))
    row = c.fetchone()
    conn.close()
    return row is not None


def create_password_reset(email):
    """Create password reset token"""
    conn = sqlite3.connect(str(DB_PATH))
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
    conn = sqlite3.connect(str(DB_PATH))
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
    """Complete password reset"""
    email, error = verify_password_reset(token)
    if error:
        return False, error
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    password_hash = hash_password(new_password)
    c.execute('UPDATE users SET password_hash = ?, updated_at = ? WHERE email = ?', 
              (password_hash, datetime.now().isoformat(), email))
    c.execute('UPDATE password_resets SET used = 1 WHERE token = ?', (token,))
    
    conn.commit()
    conn.close()
    return True, None


def update_last_login(user_id):
    """Update user's last login time"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()


def update_user(user_id, user_data):
    """Update user record"""
    conn = sqlite3.connect(str(DB_PATH))
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
    conn = sqlite3.connect(str(DB_PATH))
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
    
    # Enterprise/team plan = unlimited
    if plan == 'enterprise':
        return True, "Unlimited grants", 999
    
    remaining = max_allowed - used
    
    if remaining > 0:
        return True, f"{remaining} grants remaining this month", remaining
    else:
        return False, f"Monthly limit reached ({max_allowed}/month). Upgrade to submit more grants.", 0


def increment_grant_count(user_id):
    """Increment the user's grant count for this month"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    c.execute('UPDATE users SET grants_this_month = grants_this_month + 1 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()


def reset_monthly_grants():
    """Reset grant counts for all users at the start of a new month - run via cron"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    c.execute('UPDATE users SET grants_this_month = 0')
    affected = c.rowcount
    conn.commit()
    conn.close()
    
    return f"Reset grant counts for {affected} users"


def get_user_plan(user_id):
    """Get user's plan and limits"""
    conn = sqlite3.connect(str(DB_PATH))
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


if __name__ == '__main__':
    init_user_db()
    print("User database initialized")


# ============ ORGANIZATION ONBOARDING FUNCTIONS ============

def get_organization_details(user_id):
    """Get all organization details for a user"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    # Get organization details
    c.execute('SELECT * FROM organization_details WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    
    org_details = None
    if row:
        org_details = dict(zip(['user_id', 'ein', 'duns', 'uei', 'address_line1', 'address_line2', 
                               'city', 'state', 'zip_code', 'country', 'phone', 'website', 
                               'created_at', 'updated_at'], row))
    
    # Get organization profile
    c.execute('SELECT * FROM organization_profile WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    
    org_profile = None
    if row:
        org_profile = dict(zip(['user_id', 'annual_revenue', 'year_founded', 'employees', 'organization_type'], row))
    
    # Get focus areas
    c.execute('SELECT focus_area FROM mission_focus WHERE user_id = ?', (user_id,))
    focus_areas = [row[0] for row in c.fetchall()]
    
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
    conn = sqlite3.connect(str(DB_PATH))
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
                 (user_id, annual_revenue, year_founded, employees, organization_type)
                 VALUES (?, ?, ?, ?, ?)''',
               (user_id, 
                org_profile.get('annual_revenue'), org_profile.get('year_founded'),
                org_profile.get('employees'), org_profile.get('organization_type')))
    
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
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('SELECT onboarding_completed FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] == 1 if row else False
