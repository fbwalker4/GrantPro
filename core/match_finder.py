#!/usr/bin/env python3
"""
Match Funding Finder - Helps users find local match funding for federal grants.

Provides match source data by state, match requirement calculations,
and seed data for Mississippi programs.
"""

import uuid
from datetime import datetime

from db_connection import get_connection


# ===================================================================
# Mississippi Seed Data
# ===================================================================

MS_MATCH_SOURCES = [
    {
        "state": "MS", "source_name": "Mississippi Development Authority CDBG State Program",
        "source_type": "state_grant", "administering_agency": "Mississippi Development Authority",
        "funding_type": "grant", "amount_min": 50000, "amount_max": 500000,
        "eligible_activities": "Housing rehabilitation, infrastructure, economic development, public facilities",
        "eligible_applicants": "Local governments, nonprofits (through local gov)",
        "application_cycle": "Annual, typically October", "website_url": "https://www.mda.ms.gov",
        "description": "State-administered CDBG funds for community development projects in non-entitlement areas"
    },
    {
        "state": "MS", "source_name": "Mississippi Home Corporation HOME Program",
        "source_type": "state_grant", "administering_agency": "Mississippi Home Corporation",
        "funding_type": "grant", "amount_min": 25000, "amount_max": 500000,
        "eligible_activities": "Affordable housing construction, rehabilitation, homebuyer assistance",
        "eligible_applicants": "CHDOs, nonprofits, local governments, developers",
        "application_cycle": "Annual NOFA", "website_url": "https://www.mshomecorp.com",
        "description": "HOME Investment Partnerships funds for affordable housing"
    },
    {
        "state": "MS", "source_name": "FHLB Dallas Affordable Housing Program",
        "source_type": "fhlb", "administering_agency": "Federal Home Loan Bank of Dallas",
        "funding_type": "grant", "amount_min": 10000, "amount_max": 500000,
        "eligible_activities": "Affordable housing purchase, construction, rehabilitation",
        "eligible_applicants": "Nonprofits and government agencies through FHLB member banks",
        "application_cycle": "Annual competitive, typically spring", "website_url": "https://www.fhlb.com/community/affordable-housing-program",
        "description": "Subsidies for affordable housing through FHLB member financial institutions"
    },
    {
        "state": "MS", "source_name": "Hope Enterprise Corporation",
        "source_type": "cdfi", "administering_agency": "Hope Enterprise Corporation",
        "funding_type": "loan", "amount_min": 50000, "amount_max": 2000000,
        "eligible_activities": "Housing, community facilities, small business, healthcare",
        "eligible_applicants": "Nonprofits, small businesses, community organizations",
        "application_cycle": "Rolling", "website_url": "https://hopecu.org",
        "description": "CDFI providing loans for community development in the Deep South"
    },
    {
        "state": "MS", "source_name": "Mississippi Emergency Management Agency Hazard Mitigation",
        "source_type": "state_grant", "administering_agency": "MEMA",
        "funding_type": "grant", "amount_min": 25000, "amount_max": 1000000,
        "eligible_activities": "Flood mitigation, safe rooms, infrastructure protection",
        "eligible_applicants": "Local governments, tribal governments, nonprofits (as subapplicants)",
        "application_cycle": "Post-disaster or annual pre-disaster", "website_url": "https://www.msema.org",
        "description": "FEMA pass-through for hazard mitigation projects"
    },
    {
        "state": "MS", "source_name": "Phil Hardin Foundation",
        "source_type": "foundation", "administering_agency": "Phil Hardin Foundation",
        "funding_type": "grant", "amount_min": 5000, "amount_max": 100000,
        "eligible_activities": "Education, youth development, community improvement",
        "eligible_applicants": "501(c)(3) nonprofits in Mississippi",
        "application_cycle": "Quarterly deadlines", "website_url": "https://www.philhardin.org",
        "description": "Mississippi foundation focused on education and community development"
    },
    {
        "state": "MS", "source_name": "Riley Foundation",
        "source_type": "foundation", "administering_agency": "Riley Foundation",
        "funding_type": "grant", "amount_min": 5000, "amount_max": 50000,
        "eligible_activities": "Arts, culture, education, community development",
        "eligible_applicants": "501(c)(3) nonprofits in Mississippi",
        "application_cycle": "Annual", "website_url": "https://rfrfdn.org",
        "description": "Mississippi foundation supporting community improvement"
    },
    {
        "state": "MS", "source_name": "Community Foundation of South Mississippi",
        "source_type": "foundation", "administering_agency": "Community Foundation of South Mississippi",
        "funding_type": "grant", "amount_min": 1000, "amount_max": 25000,
        "eligible_activities": "Community development, education, health, arts on the Gulf Coast",
        "eligible_applicants": "501(c)(3) nonprofits in south Mississippi",
        "application_cycle": "Multiple cycles per year", "website_url": "https://www.communityfoundation.com",
        "description": "Local foundation for Gulf Coast community grants"
    },
    {
        "state": "MS", "source_name": "Mississippi Department of Environmental Quality SRF",
        "source_type": "state_loan", "administering_agency": "MDEQ",
        "funding_type": "loan", "amount_min": 100000, "amount_max": 10000000,
        "eligible_activities": "Water and sewer infrastructure, stormwater management",
        "eligible_applicants": "Local governments, water utilities",
        "application_cycle": "Annual priority list", "website_url": "https://www.mdeq.ms.gov",
        "description": "State Revolving Fund for water/wastewater infrastructure"
    },
    {
        "state": "MS", "source_name": "In-Kind Contributions (Staff, Volunteers, Materials)",
        "source_type": "inkind", "administering_agency": "Self",
        "funding_type": "inkind", "amount_min": 0, "amount_max": 0,
        "eligible_activities": "Staff time, volunteer labor, donated materials, equipment use",
        "eligible_applicants": "Any applicant",
        "application_cycle": "N/A -- documented per 2 CFR 200.306",
        "description": "In-kind contributions valued at fair market rates. Staff time at actual salary rate. Volunteer labor at rates per BLS data for comparable work."
    },
]


# ===================================================================
# Source type display labels and categories
# ===================================================================

SOURCE_TYPE_LABELS = {
    'state_grant': 'State Program',
    'state_loan': 'State Loan',
    'fhlb': 'FHLB',
    'cdfi': 'CDFI',
    'foundation': 'Foundation',
    'inkind': 'In-Kind',
}

SOURCE_TYPE_CATEGORIES = {
    'State Programs': ['state_grant', 'state_loan'],
    'FHLB': ['fhlb'],
    'CDFI': ['cdfi'],
    'Foundation': ['foundation'],
    'In-Kind': ['inkind'],
}

SOURCE_TYPE_BADGE_COLORS = {
    'state_grant': 'purple',
    'state_loan': 'amber',
    'fhlb': 'green',
    'cdfi': 'amber',
    'foundation': 'green',
    'inkind': 'red',
}


# ===================================================================
# Public API
# ===================================================================

def get_match_sources(state, source_type=None, amount_needed=None):
    """Get match funding sources for a state, optionally filtered.

    Args:
        state: Two-letter state code (e.g. 'MS')
        source_type: Optional filter by source_type
        amount_needed: Optional - only return sources whose amount range overlaps

    Returns:
        List of dicts, one per matching source.
    """
    conn = get_connection()
    sql = 'SELECT * FROM match_sources WHERE state = ?'
    params = [state]

    if source_type:
        sql += ' AND source_type = ?'
        params.append(source_type)

    if amount_needed and amount_needed > 0:
        # Return sources where max >= 0 (inkind has 0/0, always include)
        # or where the amount range overlaps with what's needed
        sql += ' AND (amount_max = 0 OR amount_min <= ?)'
        params.append(amount_needed)

    sql += ' ORDER BY source_type, source_name'
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return [dict(r) for r in rows]


def get_match_sources_by_category(state, amount_needed=None):
    """Get match sources grouped by category.

    Returns:
        dict of {category_name: [sources]}
    """
    all_sources = get_match_sources(state, amount_needed=amount_needed)
    categorized = {}

    for cat_name, type_codes in SOURCE_TYPE_CATEGORIES.items():
        sources_in_cat = [s for s in all_sources if s.get('source_type') in type_codes]
        if sources_in_cat:
            categorized[cat_name] = sources_in_cat

    return categorized


def calculate_match_requirement(grant_amount, match_percentage):
    """Calculate the match amount needed.

    Args:
        grant_amount: The federal grant award amount
        match_percentage: The match percentage required (e.g. 25 for 25%)

    Returns:
        dict with match_amount, total_project_cost, federal_share
    """
    if not grant_amount or not match_percentage:
        return {'match_amount': 0, 'total_project_cost': 0, 'federal_share': 0}

    match_pct = float(match_percentage) / 100.0
    # Match is typically expressed as % of total project cost
    # e.g. 25% match means federal = 75%, local = 25%
    # total_project_cost = grant_amount / (1 - match_pct)
    if match_pct >= 1.0:
        return {'match_amount': 0, 'total_project_cost': 0, 'federal_share': 0}

    total_project_cost = grant_amount / (1.0 - match_pct)
    match_amount = total_project_cost * match_pct

    return {
        'match_amount': round(match_amount, 2),
        'total_project_cost': round(total_project_cost, 2),
        'federal_share': round(grant_amount, 2),
    }


def seed_match_sources():
    """Seed the initial Mississippi match sources data.

    Idempotent -- skips if sources already exist for MS.
    """
    conn = get_connection()

    # Check if already seeded
    row = conn.execute("SELECT COUNT(*) AS cnt FROM match_sources WHERE state = ?", ('MS',)).fetchone()
    count = row['cnt'] if hasattr(row, 'keys') else row[0]

    if count and int(count) > 0:
        conn.close()
        return False  # Already seeded

    now = datetime.utcnow().isoformat()
    for src in MS_MATCH_SOURCES:
        src_id = str(uuid.uuid4())
        conn.execute(
            '''INSERT INTO match_sources
               (id, state, source_name, source_type, administering_agency,
                funding_type, amount_min, amount_max, eligible_activities,
                eligible_applicants, application_cycle, website_url,
                description, notes, last_verified, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (src_id, src['state'], src['source_name'], src['source_type'],
             src.get('administering_agency'), src.get('funding_type'),
             src.get('amount_min', 0), src.get('amount_max', 0),
             src.get('eligible_activities'), src.get('eligible_applicants'),
             src.get('application_cycle'), src.get('website_url'),
             src.get('description'), src.get('notes'), now, now)
        )

    conn.commit()
    conn.close()
    return True  # Seeded


def init_match_tables():
    """Create match_sources table if it doesn't exist (for local SQLite dev)."""
    conn = get_connection()
    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS match_sources (
            id TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_type TEXT NOT NULL,
            administering_agency TEXT,
            funding_type TEXT,
            amount_min INTEGER DEFAULT 0,
            amount_max INTEGER DEFAULT 0,
            eligible_activities TEXT,
            eligible_applicants TEXT,
            application_cycle TEXT,
            website_url TEXT,
            description TEXT,
            notes TEXT,
            last_verified TEXT,
            created_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS funding_strategies (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            grant_id TEXT,
            project_name TEXT NOT NULL,
            total_project_cost DOUBLE PRECISION DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS strategy_sources (
            id TEXT PRIMARY KEY,
            strategy_id TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_type TEXT,
            amount DOUBLE PRECISION DEFAULT 0,
            status TEXT DEFAULT 'identified',
            notes TEXT,
            created_at TEXT
        )''')
        conn.commit()
    except Exception:
        pass
    conn.close()


# ===================================================================
# Funding Strategy helpers
# ===================================================================

def get_user_strategies(user_id):
    """Get all funding strategies for a user."""
    conn = get_connection()
    rows = conn.execute(
        'SELECT * FROM funding_strategies WHERE user_id = ? ORDER BY updated_at DESC',
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_strategy(strategy_id):
    """Get a single funding strategy with its sources."""
    conn = get_connection()
    strategy = conn.execute(
        'SELECT * FROM funding_strategies WHERE id = ?', (strategy_id,)
    ).fetchone()
    if not strategy:
        conn.close()
        return None

    strategy = dict(strategy)

    sources = conn.execute(
        'SELECT * FROM strategy_sources WHERE strategy_id = ? ORDER BY amount DESC',
        (strategy_id,)
    ).fetchall()
    strategy['sources'] = [dict(s) for s in sources]

    # Calculate totals
    total_identified = sum(s.get('amount', 0) or 0 for s in strategy['sources'])
    total_secured = sum(
        (s.get('amount', 0) or 0)
        for s in strategy['sources']
        if s.get('status') == 'secured'
    )
    total_pending = sum(
        (s.get('amount', 0) or 0)
        for s in strategy['sources']
        if s.get('status') == 'applied'
    )
    project_cost = strategy.get('total_project_cost') or 0
    gap = max(0, project_cost - total_identified)

    strategy['total_identified'] = total_identified
    strategy['total_secured'] = total_secured
    strategy['total_pending'] = total_pending
    strategy['gap'] = gap

    conn.close()
    return strategy


def create_strategy(user_id, project_name, total_project_cost, grant_id=None):
    """Create a new funding strategy."""
    conn = get_connection()
    strategy_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    conn.execute(
        '''INSERT INTO funding_strategies (id, user_id, grant_id, project_name, total_project_cost, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (strategy_id, user_id, grant_id, project_name, total_project_cost, now, now)
    )
    conn.commit()
    conn.close()
    return strategy_id


def add_strategy_source(strategy_id, source_name, source_type, amount, status='identified', notes=''):
    """Add a funding source to a strategy."""
    conn = get_connection()
    source_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    conn.execute(
        '''INSERT INTO strategy_sources (id, strategy_id, source_name, source_type, amount, status, notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (source_id, strategy_id, source_name, source_type, amount, status, notes, now)
    )

    # Update strategy timestamp
    conn.execute(
        'UPDATE funding_strategies SET updated_at = ? WHERE id = ?',
        (now, strategy_id)
    )
    conn.commit()
    conn.close()
    return source_id


def update_strategy_source(source_id, amount=None, status=None, notes=None):
    """Update a strategy source."""
    conn = get_connection()
    now = datetime.utcnow().isoformat()

    updates = []
    params = []
    if amount is not None:
        updates.append('amount = ?')
        params.append(amount)
    if status is not None:
        updates.append('status = ?')
        params.append(status)
    if notes is not None:
        updates.append('notes = ?')
        params.append(notes)

    if not updates:
        conn.close()
        return

    params.append(source_id)
    conn.execute(f'UPDATE strategy_sources SET {", ".join(updates)} WHERE id = ?', params)

    # Update parent strategy timestamp
    conn.execute(
        '''UPDATE funding_strategies SET updated_at = ?
           WHERE id = (SELECT strategy_id FROM strategy_sources WHERE id = ?)''',
        (now, source_id)
    )
    conn.commit()
    conn.close()


def delete_strategy_source(source_id):
    """Remove a funding source from a strategy."""
    conn = get_connection()
    now = datetime.utcnow().isoformat()

    # Update parent strategy timestamp first
    conn.execute(
        '''UPDATE funding_strategies SET updated_at = ?
           WHERE id = (SELECT strategy_id FROM strategy_sources WHERE id = ?)''',
        (now, source_id)
    )
    conn.execute('DELETE FROM strategy_sources WHERE id = ?', (source_id,))
    conn.commit()
    conn.close()


def update_strategy(strategy_id, project_name=None, total_project_cost=None):
    """Update a funding strategy's details."""
    conn = get_connection()
    now = datetime.utcnow().isoformat()

    updates = ['updated_at = ?']
    params = [now]
    if project_name is not None:
        updates.append('project_name = ?')
        params.append(project_name)
    if total_project_cost is not None:
        updates.append('total_project_cost = ?')
        params.append(total_project_cost)

    params.append(strategy_id)
    conn.execute(f'UPDATE funding_strategies SET {", ".join(updates)} WHERE id = ?', params)
    conn.commit()
    conn.close()


def delete_strategy(strategy_id):
    """Delete a funding strategy and all its sources."""
    conn = get_connection()
    conn.execute('DELETE FROM strategy_sources WHERE strategy_id = ?', (strategy_id,))
    conn.execute('DELETE FROM funding_strategies WHERE id = ?', (strategy_id,))
    conn.commit()
    conn.close()
