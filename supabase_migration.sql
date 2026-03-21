-- ============================================================
-- GrantPro - Supabase PostgreSQL Migration
-- Creates ALL tables for the grant writing system
-- Generated: 2026-03-20
-- ============================================================

-- ============================================================
-- 1. USERS & AUTH TABLES (from user_models.py)
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
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
    onboarding_completed BOOLEAN DEFAULT FALSE,
    created_at TEXT,
    updated_at TEXT,
    last_login TEXT
);

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    bio TEXT,
    interests TEXT,
    eligible_entities TEXT,
    funding_amount_min INTEGER,
    funding_amount_max INTEGER,
    preferred_categories TEXT,
    notify_deadlines BOOLEAN DEFAULT TRUE,
    notify_new_grants BOOLEAN DEFAULT TRUE,
    reminder_days TEXT DEFAULT '7,3,1'
);

CREATE TABLE IF NOT EXISTS saved_grants (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    grant_id TEXT NOT NULL,
    notes TEXT,
    saved_at TEXT,
    UNIQUE(user_id, grant_id)
);

CREATE TABLE IF NOT EXISTS user_applications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    grant_id TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    progress INTEGER DEFAULT 0,
    started_at TEXT,
    updated_at TEXT,
    submitted_at TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS password_resets (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    token TEXT NOT NULL,
    created_at TEXT,
    expires_at TEXT,
    used BOOLEAN DEFAULT FALSE
);

-- ============================================================
-- 2. ORGANIZATION TABLES (from user_models.py)
-- ============================================================

CREATE TABLE IF NOT EXISTS organization_details (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
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
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS organization_profile (
    user_id TEXT PRIMARY KEY REFERENCES users(id),
    annual_revenue TEXT,
    year_founded INTEGER,
    employees TEXT,
    organization_type TEXT,
    mission_statement TEXT,
    programs_description TEXT
);

CREATE TABLE IF NOT EXISTS mission_focus (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    focus_area TEXT NOT NULL,
    UNIQUE(user_id, focus_area)
);

CREATE TABLE IF NOT EXISTS past_grant_experience (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    grant_name TEXT,
    funding_organization TEXT,
    year_received INTEGER,
    amount_received INTEGER,
    status TEXT
);

-- ============================================================
-- 3. CORE GRANT SYSTEM TABLES (from grant_db.py)
-- ============================================================

CREATE TABLE IF NOT EXISTS clients (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    organization_name TEXT,
    contact_name TEXT,
    contact_email TEXT,
    status TEXT DEFAULT 'new',
    current_stage TEXT DEFAULT 'new',
    created_at TEXT,
    updated_at TEXT,
    intake_data TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS grants (
    id TEXT PRIMARY KEY,
    client_id TEXT REFERENCES clients(id),
    grant_name TEXT,
    agency TEXT,
    amount DOUBLE PRECISION,
    deadline TEXT,
    status TEXT DEFAULT 'research',
    assigned_at TEXT,
    submitted_at TEXT,
    result TEXT,
    opportunity_number TEXT,
    cfda TEXT,
    template TEXT,
    -- Submission tracking columns (from app.py migration)
    submission_date TEXT,
    confirmation_number TEXT,
    portal_used TEXT,
    submission_notes TEXT,
    amount_funded DOUBLE PRECISION,
    rejection_reason TEXT,
    notification_date TEXT
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    client_id TEXT REFERENCES clients(id),
    doc_type TEXT,
    file_path TEXT,
    uploaded_at TEXT,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    client_id TEXT REFERENCES clients(id),
    invoice_type TEXT,
    amount DOUBLE PRECISION,
    status TEXT DEFAULT 'pending',
    created_at TEXT,
    paid_at TEXT,
    grant_id TEXT
);

CREATE TABLE IF NOT EXISTS drafts (
    id TEXT PRIMARY KEY,
    client_id TEXT REFERENCES clients(id),
    grant_id TEXT REFERENCES grants(id),
    section TEXT,
    content TEXT,
    version INTEGER DEFAULT 1,
    created_at TEXT,
    updated_at TEXT,
    status TEXT DEFAULT 'draft'
);

-- ============================================================
-- 4. GRANTS CATALOG (from grant_db.py)
-- ============================================================

CREATE TABLE IF NOT EXISTS grants_catalog (
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
);

-- ============================================================
-- 5. AWARDS & TESTIMONIALS (from grant_db.py)
-- ============================================================

CREATE TABLE IF NOT EXISTS award_matches (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    grant_id TEXT,
    grant_name TEXT,
    award_amount DOUBLE PRECISION,
    award_date TEXT,
    source TEXT,
    notified BOOLEAN DEFAULT FALSE,
    testimonial_token TEXT UNIQUE,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS testimonials (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    award_match_id TEXT,
    rating INTEGER,
    text TEXT,
    org_name TEXT,
    contact_name TEXT,
    approved BOOLEAN DEFAULT FALSE,
    created_at TEXT
);

-- ============================================================
-- 5b. GRANT BUDGET (structured budget builder)
-- ============================================================

CREATE TABLE IF NOT EXISTS grant_budget (
    id TEXT PRIMARY KEY,
    grant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    project_title TEXT,
    requested_amount DOUBLE PRECISION DEFAULT 0,
    project_duration_months INTEGER DEFAULT 12,
    personnel TEXT DEFAULT '[]',
    fringe_rate DOUBLE PRECISION DEFAULT 30,
    fringe_total DOUBLE PRECISION DEFAULT 0,
    travel_items TEXT DEFAULT '[]',
    travel_total DOUBLE PRECISION DEFAULT 0,
    equipment_items TEXT DEFAULT '[]',
    equipment_total DOUBLE PRECISION DEFAULT 0,
    supplies_total DOUBLE PRECISION DEFAULT 0,
    supplies_description TEXT,
    contractual_items TEXT DEFAULT '[]',
    contractual_total DOUBLE PRECISION DEFAULT 0,
    construction_total DOUBLE PRECISION DEFAULT 0,
    other_items TEXT DEFAULT '[]',
    other_total DOUBLE PRECISION DEFAULT 0,
    participant_support_total DOUBLE PRECISION DEFAULT 0,
    participant_support_description TEXT,
    total_direct DOUBLE PRECISION DEFAULT 0,
    indirect_rate DOUBLE PRECISION DEFAULT 15,
    indirect_rate_type TEXT DEFAULT 'de_minimis',
    mtdc_base DOUBLE PRECISION DEFAULT 0,
    indirect_total DOUBLE PRECISION DEFAULT 0,
    grand_total DOUBLE PRECISION DEFAULT 0,
    match_cash DOUBLE PRECISION DEFAULT 0,
    match_inkind DOUBLE PRECISION DEFAULT 0,
    match_total DOUBLE PRECISION DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_grant_budget_grant_id ON grant_budget(grant_id);
CREATE INDEX IF NOT EXISTS idx_grant_budget_user_id ON grant_budget(user_id);

-- ============================================================
-- 6. GUEST & LEAD TABLES (from app.py)
-- ============================================================

CREATE TABLE IF NOT EXISTS guest_saves (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    grant_id TEXT NOT NULL,
    notes TEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    source TEXT DEFAULT 'landing_page'
);

-- ============================================================
-- 7. INDEXES
-- ============================================================

-- Users
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_plan ON users(plan);
CREATE INDEX IF NOT EXISTS idx_users_subscription_status ON users(subscription_status);
CREATE INDEX IF NOT EXISTS idx_users_stripe_customer_id ON users(stripe_customer_id);

-- User profiles
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);

-- Saved grants
CREATE INDEX IF NOT EXISTS idx_saved_grants_user_id ON saved_grants(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_grants_grant_id ON saved_grants(grant_id);

-- User applications
CREATE INDEX IF NOT EXISTS idx_user_applications_user_id ON user_applications(user_id);
CREATE INDEX IF NOT EXISTS idx_user_applications_grant_id ON user_applications(grant_id);
CREATE INDEX IF NOT EXISTS idx_user_applications_status ON user_applications(status);

-- Password resets
CREATE INDEX IF NOT EXISTS idx_password_resets_email ON password_resets(email);
CREATE INDEX IF NOT EXISTS idx_password_resets_token ON password_resets(token);

-- Organization
CREATE INDEX IF NOT EXISTS idx_organization_details_user_id ON organization_details(user_id);
CREATE INDEX IF NOT EXISTS idx_mission_focus_user_id ON mission_focus(user_id);
CREATE INDEX IF NOT EXISTS idx_past_grant_experience_user_id ON past_grant_experience(user_id);

-- Clients
CREATE INDEX IF NOT EXISTS idx_clients_user_id ON clients(user_id);
CREATE INDEX IF NOT EXISTS idx_clients_status ON clients(status);

-- Grants
CREATE INDEX IF NOT EXISTS idx_grants_client_id ON grants(client_id);
CREATE INDEX IF NOT EXISTS idx_grants_status ON grants(status);

-- Documents
CREATE INDEX IF NOT EXISTS idx_documents_client_id ON documents(client_id);

-- Invoices
CREATE INDEX IF NOT EXISTS idx_invoices_client_id ON invoices(client_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_grant_id ON invoices(grant_id);

-- Drafts
CREATE INDEX IF NOT EXISTS idx_drafts_client_id ON drafts(client_id);
CREATE INDEX IF NOT EXISTS idx_drafts_grant_id ON drafts(grant_id);

-- Grants catalog
CREATE INDEX IF NOT EXISTS idx_grants_catalog_status ON grants_catalog(status);
CREATE INDEX IF NOT EXISTS idx_grants_catalog_agency_code ON grants_catalog(agency_code);
CREATE INDEX IF NOT EXISTS idx_grants_catalog_close_date ON grants_catalog(close_date);
CREATE INDEX IF NOT EXISTS idx_grants_catalog_opportunity_number ON grants_catalog(opportunity_number);

-- Award matches
CREATE INDEX IF NOT EXISTS idx_award_matches_user_id ON award_matches(user_id);
CREATE INDEX IF NOT EXISTS idx_award_matches_grant_id ON award_matches(grant_id);

-- Testimonials
CREATE INDEX IF NOT EXISTS idx_testimonials_user_id ON testimonials(user_id);
CREATE INDEX IF NOT EXISTS idx_testimonials_approved ON testimonials(approved);

-- Guest saves
CREATE INDEX IF NOT EXISTS idx_guest_saves_email ON guest_saves(email);
CREATE INDEX IF NOT EXISTS idx_guest_saves_grant_id ON guest_saves(grant_id);

-- Leads
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
