#!/usr/bin/env python3
"""
Grant Writing System - AI Core
Local grant writing assistant using LLM
"""

import json
import os
import sqlite3
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
    
    conn.commit()
    conn.close()
    return DB_PATH

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
