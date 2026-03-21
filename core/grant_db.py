#!/usr/bin/env python3
"""
Grant Writing System - AI Core
Local grant writing assistant using LLM
"""

import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Database setup
from db_connection import LOCAL_DB_PATH as DB_PATH
from db_connection import get_connection

def init_db():
    """Initialize the grants database.

    On Postgres (Supabase) the schema is applied via supabase_migration.sql,
    so CREATE TABLE may fail.  Wrapped in try/except for graceful handling.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    c = conn.cursor()

    try:
        # Clients table
        c.execute('''CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            organization_name TEXT,
            contact_name TEXT,
            contact_email TEXT,
            status TEXT DEFAULT 'new',
            current_stage TEXT DEFAULT 'new',
            created_at TEXT,
            updated_at TEXT,
            intake_data TEXT,
            notes TEXT
        )''')

        # Grants table
        c.execute('''CREATE TABLE IF NOT EXISTS grants (
            id TEXT PRIMARY KEY,
            client_id TEXT,
            grant_name TEXT,
            agency TEXT,
            amount REAL,
            deadline TEXT,
            status TEXT DEFAULT 'research',
            assigned_at TEXT,
            submitted_at TEXT,
            result TEXT,
            opportunity_number TEXT,
            cfda TEXT,
            template TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )''')

        # Documents table
        c.execute('''CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            client_id TEXT,
            doc_type TEXT,
            file_path TEXT,
            uploaded_at TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )''')

        # Invoices table
        c.execute('''CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            client_id TEXT,
            invoice_type TEXT,
            amount REAL,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            paid_at TEXT,
            grant_id TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )''')

        # Drafts table
        c.execute('''CREATE TABLE IF NOT EXISTS drafts (
            id TEXT PRIMARY KEY,
            client_id TEXT,
            grant_id TEXT,
            section TEXT,
            content TEXT,
            version INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT,
            status TEXT DEFAULT 'draft',
            FOREIGN KEY (client_id) REFERENCES clients(id),
            FOREIGN KEY (grant_id) REFERENCES grants(id)
        )''')

        # Grants catalog table - unified grants directory (seed + Grants.gov)
        c.execute('''CREATE TABLE IF NOT EXISTS grants_catalog (
            id TEXT PRIMARY KEY,
            opportunity_number TEXT,
            title TEXT NOT NULL,
            agency TEXT,
            agency_code TEXT,
            cfda TEXT,
            category TEXT,
            amount_min INTEGER DEFAULT 0,
            amount_max INTEGER DEFAULT 0,
            open_date TEXT,
            close_date TEXT,
            description TEXT,
            eligibility TEXT,
            url TEXT,
            template TEXT DEFAULT 'generic',
            source TEXT DEFAULT 'seed',
            status TEXT DEFAULT 'active',
            created_at TEXT,
            updated_at TEXT
        )''')

        # Award matches table - tracks grant awards matched to our users
        c.execute('''CREATE TABLE IF NOT EXISTS award_matches (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            grant_id TEXT,
            grant_name TEXT,
            award_amount REAL,
            award_date TEXT,
            source TEXT,
            notified INTEGER DEFAULT 0,
            testimonial_token TEXT UNIQUE,
            created_at TEXT
        )''')

        # Testimonials table - user-submitted testimonials linked to awards
        c.execute('''CREATE TABLE IF NOT EXISTS testimonials (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            award_match_id TEXT,
            rating INTEGER,
            text TEXT,
            org_name TEXT,
            contact_name TEXT,
            approved INTEGER DEFAULT 0,
            created_at TEXT
        )''')

        # Grant documents table - uploaded and generated documents for submissions
        c.execute('''CREATE TABLE IF NOT EXISTS grant_documents (
            id TEXT PRIMARY KEY,
            grant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            doc_name TEXT NOT NULL,
            file_path TEXT,
            file_data BYTEA,
            status TEXT DEFAULT 'pending',
            generated BOOLEAN DEFAULT FALSE,
            created_at TEXT,
            updated_at TEXT
        )''')

        # Grant readiness profile - eligibility screening data
        c.execute('''CREATE TABLE IF NOT EXISTS grant_readiness (
            user_id TEXT PRIMARY KEY,
            applicant_category TEXT,
            is_501c3 BOOLEAN DEFAULT FALSE,
            is_government BOOLEAN DEFAULT FALSE,
            government_type TEXT,
            is_pha BOOLEAN DEFAULT FALSE,
            is_chdo BOOLEAN DEFAULT FALSE,
            is_university BOOLEAN DEFAULT FALSE,
            is_small_business BOOLEAN DEFAULT FALSE,
            employee_count INTEGER,
            sam_gov_status TEXT DEFAULT 'unknown',
            sam_gov_expiry TEXT,
            has_uei BOOLEAN DEFAULT FALSE,
            has_grants_gov BOOLEAN DEFAULT FALSE,
            has_indirect_rate BOOLEAN DEFAULT FALSE,
            indirect_rate_type TEXT,
            indirect_rate_pct REAL,
            cognizant_agency TEXT,
            had_single_audit BOOLEAN DEFAULT FALSE,
            annual_federal_funding INTEGER DEFAULT 0,
            largest_federal_grant INTEGER DEFAULT 0,
            has_construction_experience BOOLEAN DEFAULT FALSE,
            has_grants_administrator BOOLEAN DEFAULT FALSE,
            funding_purposes TEXT,
            funding_range_min INTEGER DEFAULT 0,
            funding_range_max INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )''')

        # Grant shares table - shareable read-only links for review
        c.execute('''CREATE TABLE IF NOT EXISTS grant_shares (
            id TEXT PRIMARY KEY,
            grant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            share_token TEXT UNIQUE NOT NULL,
            recipient_name TEXT,
            recipient_email TEXT,
            permission TEXT DEFAULT 'view',
            expires_at TEXT,
            created_at TEXT
        )''')

        # Grant checklist table - submission readiness checklist items
        c.execute('''CREATE TABLE IF NOT EXISTS grant_checklist (
            id TEXT PRIMARY KEY,
            grant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            item_type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            description TEXT,
            required BOOLEAN DEFAULT TRUE,
            completed BOOLEAN DEFAULT FALSE,
            completed_by TEXT,
            completed_at TEXT,
            notes TEXT
        )''')

        # Grant budget table - structured budget builder data
        c.execute('''CREATE TABLE IF NOT EXISTS grant_budget (
            id TEXT PRIMARY KEY,
            grant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            project_title TEXT,
            requested_amount REAL DEFAULT 0,
            project_duration_months INTEGER DEFAULT 12,
            personnel TEXT DEFAULT '[]',
            fringe_rate REAL DEFAULT 30,
            fringe_total REAL DEFAULT 0,
            travel_items TEXT DEFAULT '[]',
            travel_total REAL DEFAULT 0,
            equipment_items TEXT DEFAULT '[]',
            equipment_total REAL DEFAULT 0,
            supplies_total REAL DEFAULT 0,
            supplies_description TEXT,
            contractual_items TEXT DEFAULT '[]',
            contractual_total REAL DEFAULT 0,
            construction_total REAL DEFAULT 0,
            other_items TEXT DEFAULT '[]',
            other_total REAL DEFAULT 0,
            participant_support_total REAL DEFAULT 0,
            participant_support_description TEXT,
            total_direct REAL DEFAULT 0,
            indirect_rate REAL DEFAULT 15,
            indirect_rate_type TEXT DEFAULT 'de_minimis',
            mtdc_base REAL DEFAULT 0,
            indirect_total REAL DEFAULT 0,
            grand_total REAL DEFAULT 0,
            match_cash REAL DEFAULT 0,
            match_inkind REAL DEFAULT 0,
            match_total REAL DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )''')
    except Exception as e:
        # On Postgres the schema is managed by supabase_migration.sql
        import logging
        logging.getLogger(__name__).info("init_db migration note (expected on Postgres): %s", e)

    try:
        conn.commit()
    except Exception:
        pass
    conn.close()
    return DB_PATH


def seed_grants_catalog():
    """Seed grants_catalog from iot_grants_db.json and hardcoded grants if table is empty."""
    conn = get_connection()
    c = conn.cursor()

    count = c.execute('SELECT COUNT(*) FROM grants_catalog').fetchone()[0]
    if count > 0:
        conn.close()
        return count  # Already seeded

    now = datetime.now().isoformat()

    # Agency code to template mapping
    agency_template_map = {
        "NSF": "nsf", "DOE": "doe", "NIH": "nih", "USDA": "usda",
        "EPA": "epa", "DOT": "dot", "NIST": "nist", "HHS": "hhs",
        "DOD": "dod", "NASA": "generic", "DHS": "generic", "EDA": "generic",
        "NEA": "nea", "STATE": "generic", "PRIVATE": "generic",
    }

    inserted = 0

    # 1) Load seed data from iot_grants_db.json
    json_path = Path.home() / ".hermes" / "grant-system" / "research" / "iot_grants_db.json"
    if json_path.exists():
        with open(json_path) as f:
            data = json.load(f)
        for g in data.get('grants', []):
            agency_name = g.get('agency', '')
            # Derive agency_code from known agency names
            code = _guess_agency_code(agency_name)
            template = agency_template_map.get(code, g.get('template', 'generic'))
            c.execute('''INSERT OR IGNORE INTO grants_catalog
                (id, opportunity_number, title, agency, agency_code, cfda, category,
                 amount_min, amount_max, open_date, close_date, description, eligibility,
                 url, template, source, status, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (g['id'], g.get('opportunity_number', ''), g.get('name', g.get('title', '')),
                 agency_name, code, g.get('cfda', ''), ', '.join(g.get('focus_areas', [])),
                 g.get('amount_min', 0), g.get('amount_max', 0),
                 None, g.get('deadline', ''), g.get('description', ''),
                 g.get('eligibility', ''), g.get('url', ''), template,
                 'seed', g.get('status', 'active'), now, now))
            inserted += 1

    # 2) Load hardcoded grants from GrantResearcher._get_federal_grants()
    try:
        sys.path.insert(0, str(Path.home() / ".hermes" / "grant-system" / "research"))
        from grant_researcher import GrantResearcher
        researcher = GrantResearcher()
        for g in researcher._get_federal_grants():
            code = g.get('agency_code', '')
            template = g.get('template', agency_template_map.get(code, 'generic'))
            c.execute('''INSERT OR IGNORE INTO grants_catalog
                (id, opportunity_number, title, agency, agency_code, cfda, category,
                 amount_min, amount_max, open_date, close_date, description, eligibility,
                 url, template, source, status, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (g['id'], g.get('opportunity_number', ''), g.get('title', ''),
                 g.get('agency', ''), code, g.get('cfda', ''), g.get('category', ''),
                 g.get('amount_min', 0), g.get('amount_max', 0),
                 None, g.get('deadline', ''), g.get('description', ''),
                 g.get('eligibility', ''), g.get('url', ''), template,
                 'seed', 'active', now, now))
            inserted += 1
    except Exception as e:
        print(f"Warning: could not load hardcoded grants: {e}")

    conn.commit()
    conn.close()
    return inserted


def get_catalog_grants(status='active'):
    """Return all grants from grants_catalog with given status."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    if status:
        rows = conn.execute(
            'SELECT * FROM grants_catalog WHERE status = ? ORDER BY close_date ASC', (status,)
        ).fetchall()
    else:
        rows = conn.execute('SELECT * FROM grants_catalog ORDER BY close_date ASC').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_catalog_grants_count(status='active'):
    """Return count of active grants in catalog."""
    conn = get_connection()
    row = conn.execute(
        'SELECT COUNT(*) FROM grants_catalog WHERE status = ?', (status,)
    ).fetchone()
    conn.close()
    if not row:
        return 0
    return row.get('count', row[0]) if hasattr(row, 'get') else row[0]


def _guess_agency_code(agency_name):
    """Best-effort agency name to code mapping."""
    name = agency_name.lower()
    mapping = [
        ('national science foundation', 'NSF'), ('nsf', 'NSF'),
        ('department of energy', 'DOE'), ('arpa-e', 'DOE'),
        ('national institutes of health', 'NIH'), ('nih', 'NIH'),
        ('usda', 'USDA'), ('rural development', 'USDA'),
        ('environmental protection', 'EPA'), ('epa', 'EPA'),
        ('department of transportation', 'DOT'), ('dot', 'DOT'),
        ('nist', 'NIST'), ('standards and technology', 'NIST'),
        ('homeland security', 'DHS'), ('dhs', 'DHS'),
        ('economic development', 'EDA'), ('eda', 'EDA'),
        ('nasa', 'NASA'), ('aeronautics', 'NASA'),
        ('federal aviation', 'DOT'), ('faa', 'DOT'),
        ('commerce', 'DOC'), ('hud', 'HUD'),
        ('housing and urban', 'HUD'),
        ('health and human', 'HHS'),
        ('defense', 'DOD'), ('dod', 'DOD'),
        ('endowment for the arts', 'NEA'),
        ('mississippi', 'STATE'),
    ]
    for keyword, code in mapping:
        if keyword in name:
            return code
    return 'OTHER'

def add_client(org_name, contact_name, contact_email, intake_data=None):
    """Add a new client to the system"""
    conn = get_connection()
    c = conn.cursor()
    
    client_id = f"client-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    now = datetime.now().isoformat()
    
    c.execute('''INSERT INTO clients (id, organization_name, contact_name, contact_email, status, current_stage, created_at, updated_at, intake_data)
                 VALUES (?, ?, ?, ?, 'new', 'intake', ?, ?, ?)''',
              (client_id, org_name, contact_name, contact_email, now, now, json.dumps(intake_data or {})))
    
    conn.commit()
    conn.close()
    return client_id

def add_grant(client_id, grant_info):
    """Assign a grant to a client"""
    conn = get_connection()
    c = conn.cursor()
    
    grant_id = f"grant-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    now = datetime.now().isoformat()
    
    c.execute('''INSERT INTO grants (id, client_id, grant_name, agency, amount, deadline, status, assigned_at)
                 VALUES (?, ?, ?, ?, ?, ?, 'assigned', ?)''',
              (grant_id, client_id, grant_info['name'], grant_info['agency'], 
               grant_info.get('amount', 0), grant_info.get('deadline', ''), now))
    
    conn.commit()
    conn.close()
    return grant_id

def save_draft(client_id, grant_id, section, content, version=1):
    """Save a grant draft section"""
    conn = get_connection()
    c = conn.cursor()
    
    draft_id = f"draft-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    now = datetime.now().isoformat()
    
    c.execute('''INSERT OR REPLACE INTO drafts (id, client_id, grant_id, section, content, version, created_at, updated_at, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft')''',
              (draft_id, client_id, grant_id, section, content, version, now, now))
    
    conn.commit()
    conn.close()
    return draft_id

def create_invoice(client_id, invoice_type, amount, grant_id=None):
    """Create an invoice"""
    conn = get_connection()
    c = conn.cursor()
    
    invoice_id = f"inv-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    now = datetime.now().isoformat()
    
    c.execute('''INSERT INTO invoices (id, client_id, invoice_type, amount, status, created_at)
                 VALUES (?, ?, ?, ?, 'pending', ?)''',
              (invoice_id, client_id, invoice_type, amount, now))
    
    conn.commit()
    conn.close()
    return invoice_id

def get_client(client_id):
    """Get client details"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row) if hasattr(row, 'keys') else dict(zip(['id', 'organization_name', 'contact_name', 'contact_email', 'status', 'current_stage', 'created_at', 'updated_at', 'intake_data', 'notes'], row))

def list_clients(status=None):
    """List all clients, optionally filtered by status"""
    conn = get_connection()
    c = conn.cursor()
    if status:
        c.execute('SELECT * FROM clients WHERE status = ? ORDER BY updated_at DESC', (status,))
    else:
        c.execute('SELECT * FROM clients ORDER BY updated_at DESC')
    rows = c.fetchall()
    conn.close()
    return [dict(row) if hasattr(row, 'keys') else dict(zip(['id', 'organization_name', 'contact_name', 'contact_email', 'status', 'current_stage', 'created_at', 'updated_at', 'intake_data', 'notes'], row)) for row in rows]

def update_client_status(client_id, status, stage=None):
    """Update client status"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    if stage:
        c.execute('UPDATE clients SET status = ?, current_stage = ?, updated_at = ? WHERE id = ?', (status, stage, now, client_id))
    else:
        c.execute('UPDATE clients SET status = ?, updated_at = ? WHERE id = ?', (status, now, client_id))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print(f"Grant system database initialized at: {DB_PATH}")
