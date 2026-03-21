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
DB_PATH = Path.home() / ".hermes" / "grant-system" / "tracking" / "grants.db"

def init_db():
    """Initialize the grants database"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
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

    conn.commit()
    conn.close()
    return DB_PATH


def seed_grants_catalog():
    """Seed grants_catalog from iot_grants_db.json and hardcoded grants if table is empty."""
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
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
    conn = sqlite3.connect(str(DB_PATH))
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
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        'SELECT COUNT(*) FROM grants_catalog WHERE status = ?', (status,)
    ).fetchone()
    conn.close()
    return row[0] if row else 0


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
    conn = sqlite3.connect(str(DB_PATH))
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
    conn = sqlite3.connect(str(DB_PATH))
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
    conn = sqlite3.connect(str(DB_PATH))
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
    conn = sqlite3.connect(str(DB_PATH))
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
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
    row = c.fetchone()
    conn.close()
    return dict(zip(['id', 'organization_name', 'contact_name', 'contact_email', 'status', 'current_stage', 'created_at', 'updated_at', 'intake_data', 'notes'], row)) if row else None

def list_clients(status=None):
    """List all clients, optionally filtered by status"""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    if status:
        c.execute('SELECT * FROM clients WHERE status = ? ORDER BY updated_at DESC', (status,))
    else:
        c.execute('SELECT * FROM clients ORDER BY updated_at DESC')
    rows = c.fetchall()
    conn.close()
    return [dict(zip(['id', 'organization_name', 'contact_name', 'contact_email', 'status', 'current_stage', 'created_at', 'updated_at', 'intake_data', 'notes'], row)) for row in rows]

def update_client_status(client_id, status, stage=None):
    """Update client status"""
    conn = sqlite3.connect(str(DB_PATH))
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
