#!/usr/bin/env python3
"""
FHLB Grant Scraper for GrantPro — Dallas + Atlanta

Scrapes FHLB Dallas (fhlb.com) and FHLB Atlanta (corp.fhlbatl.com)
for affordable housing and community development grant programs.

Usage:
    python3 jobs/scrape_fhlb.py

Covers:
    - FHLB Dallas: AR, LA, MS, NM, TX
    - FHLB Atlanta: AL, FL, GA, NC, SC, VA, WV
"""
import os, sys, requests, re, psycopg2, urllib.parse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(SCRIPT_DIR, '..', '.env')
if os.path.exists(env_path):
    for line in open(env_path):
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, _, v = line.partition('=')
            os.environ[k.strip()] = v.strip()

DB_URL = os.environ.get('DATABASE_URL', '')
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; GrantProBot/1.0)'}

PROGRAMS = [
    # ── FHLB Dallas (primary for Mississippi) ──────────────────────────────
    {
        'source': 'fhlb-dallas', 'bank': 'Federal Home Loan Bank of Dallas',
        'id': 'fhlb-dallas-ahp-general', 'opp': 'FHLBD-AHP-GEN',
        'name': 'AHP General Fund',
        'desc': 'Competitive grant for purchase, construction, rehabilitation of owner-occupied, rental, or transitional housing for income-qualified households.',
        'elig': 'Housing authorities, nonprofits, developers. Must use FHLB Dallas member institution as sponsor.',
        'min': 10000, 'max': 1750000,
        'open': '2026-03-31', 'close': '2026-04-30',
        'type': 'competitive', 'category': 'affordable_housing',
        'url': 'https://www.fhlb.com/community-programs/affordable-housing-program-general-fund'
    },
    {
        'source': 'fhlb-dallas', 'bank': 'Federal Home Loan Bank of Dallas',
        'id': 'fhlb-dallas-help', 'opp': 'FHLBD-HELP',
        'name': 'Homebuyer Equity Leverage Partnership (HELP)',
        'desc': 'Down payment and closing cost assistance for first-time homebuyers. Up to $20,000 per homeowner.',
        'elig': 'First-time homebuyers at or below AMI limits. Must use FHLB member institution.',
        'min': 1000, 'max': 20000,
        'open': '2026-01-01', 'close': '2026-12-31',
        'type': 'downpayment', 'category': 'homeownership',
        'url': 'https://www.fhlb.com/community-programs/homeownership-and-homebuyer-programs/homebuyer-equity-leverage-partnership'
    },
    {
        'source': 'fhlb-dallas', 'bank': 'Federal Home Loan Bank of Dallas',
        'id': 'fhlb-dallas-dra', 'opp': 'FHLBD-DRA',
        'name': 'Disaster Rebuilding Assistance (DRA)',
        'desc': 'Repair/rehabilitation of owner-occupied housing in FEMA-declared disaster areas. Up to $15,000 per homeowner.',
        'elig': 'Homeowners at or below 80% AMI in FEMA-declared disaster areas in FHLB Dallas district.',
        'min': 5000, 'max': 15000,
        'open': '2026-01-01', 'close': '2026-12-31',
        'type': 'disaster', 'category': 'disaster_recovery',
        'url': 'https://www.fhlb.com/community-programs/disaster-recovery-assistance-programs/disaster-rebuilding-assistance'
    },
    {
        'source': 'fhlb-dallas', 'bank': 'Federal Home Loan Bank of Dallas',
        'id': 'fhlb-dallas-snap', 'opp': 'FHLBD-SNAP',
        'name': 'Special Needs Assistance Program (SNAP)',
        'desc': 'Housing rehabilitation/modification for households with special-needs occupants. $12,000 per household.',
        'elig': 'Owner-occupied households with special-needs occupant in FHLB Dallas district.',
        'min': 5000, 'max': 12000,
        'open': '2026-02-01', 'close': '2026-12-31',
        'type': 'special_needs', 'category': 'special_needs_housing',
        'url': 'https://www.fhlb.com/community-programs/homeownership-and-homebuyer-programs/special-needs-assistance-program'
    },
    {
        'source': 'fhlb-dallas', 'bank': 'Federal Home Loan Bank of Dallas',
        'id': 'fhlb-dallas-heirs', 'opp': 'FHLBD-HEIRS',
        'name': "Heirs' Property Program",
        'desc': 'Up to $150,000 for remediation of heirs property title issues; up to $25,000 for preventative legal services.',
        'elig': 'Nonprofits, governmental entities, or federally recognized tribes.',
        'min': 10000, 'max': 150000,
        'open': '2026-09-02', 'close': '2026-09-25',
        'type': 'competitive', 'category': 'homeownership',
        'url': 'https://www.fhlb.com/community-programs/homeownership-and-homebuyer-programs/heirs-property-program'
    },
    {
        'source': 'fhlb-dallas', 'bank': 'Federal Home Loan Bank of Dallas',
        'id': 'fhlb-dallas-fortified', 'opp': 'FHLBD-FORTIFIED',
        'name': 'FHLB Dallas FORTIFIED Fund',
        'desc': 'Grants for storm-resistant roofs with FORTIFIED certification. Up to $15,000 per homeowner for roof replacement.',
        'elig': 'Homeowners at or below 120% AMI.',
        'min': 5000, 'max': 15000,
        'open': '2026-01-01', 'close': '2026-12-31',
        'type': 'reimbursement', 'category': 'housing_rehabilitation',
        'url': 'https://www.fhlb.com/community-programs/homeownership-and-homebuyer-programs/fhlb-dallas-fortified-fund'
    },
    {
        'source': 'fhlb-dallas', 'bank': 'Federal Home Loan Bank of Dallas',
        'id': 'fhlb-dallas-haven', 'opp': 'FHLBD-HAVEN',
        'name': 'Housing Assistance for Veterans (HAVEN)',
        'desc': 'Home modifications, new construction, down payment assistance for veterans with service-related disabilities.',
        'elig': 'Veterans and reservists with service-related disability; Gold Star Families.',
        'min': 5000, 'max': 50000,
        'open': '2026-01-01', 'close': '2026-12-31',
        'type': 'competitive', 'category': 'veterans_housing',
        'url': 'https://www.fhlb.com/community-programs/homeownership-and-homebuyer-programs/veterans-assistance'
    },
    {
        'source': 'fhlb-dallas', 'bank': 'Federal Home Loan Bank of Dallas',
        'id': 'fhlb-dallas-naho', 'opp': 'FHLBD-NAHO',
        'name': 'Native American Housing Opportunities (NAHO) Fund',
        'desc': 'Support tribal housing needs. $50,000 to $250,000 per grant.',
        'elig': 'Federally recognized tribes and Tribally Designated Housing Entities (TDHEs).',
        'min': 50000, 'max': 250000,
        'open': '2026-06-01', 'close': '2026-06-30',
        'type': 'competitive', 'category': 'tribal_housing',
        'url': 'https://www.fhlb.com/community-programs/homeownership-and-homebuyer-programs/native-american-housing-opportunities-(naho)-fund'
    },
    {
        'source': 'fhlb-dallas', 'bank': 'Federal Home Loan Bank of Dallas',
        'id': 'fhlb-dallas-pgp', 'opp': 'FHLBD-PGP',
        'name': 'Partnership Grant Program (PGP)',
        'desc': 'Operational funding for community-based organizations (501(c)(3)). Up to $25,000 with 5:1 match.',
        'elig': '501(c)(3) community-based organizations with annual revenue $1M or less. Must have FHLB member sponsor.',
        'min': 5000, 'max': 25000,
        'open': '2026-05-05', 'close': '2026-05-22',
        'type': 'matching', 'category': 'capacity_building',
        'url': 'https://www.fhlb.com/community-programs/small-business-and-economic-development-programs/partnership-grant-program'
    },
    {
        'source': 'fhlb-dallas', 'bank': 'Federal Home Loan Bank of Dallas',
        'id': 'fhlb-dallas-cip', 'opp': 'FHLBD-CIP',
        'name': 'Community Investment Program (CIP)',
        'desc': 'Favorably priced advances (loans) for affordable housing for households up to 115% AMI. Noncompetitive, year-round.',
        'elig': 'All FHLB member institutions on behalf of affordable housing developers.',
        'min': 50000, 'max': 500000,
        'open': '2026-01-01', 'close': '2026-12-31',
        'type': 'loan', 'category': 'affordable_housing',
        'url': 'https://www.fhlb.com/community-programs/small-business-and-economic-development-programs/community-investment-program'
    },
    {
        'source': 'fhlb-dallas', 'bank': 'Federal Home Loan Bank of Dallas',
        'id': 'fhlb-dallas-edp', 'opp': 'FHLBD-EDP',
        'name': 'Economic Development Program (EDP)',
        'desc': 'Favorably priced advances for qualified economic and commercial development projects. Noncompetitive, year-round.',
        'elig': 'All FHLB member institutions on behalf of economic development projects.',
        'min': 50000, 'max': 500000,
        'open': '2026-01-01', 'close': '2026-12-31',
        'type': 'loan', 'category': 'economic_development',
        'url': 'https://www.fhlb.com/community-programs/small-business-and-economic-development-programs/economic-development-program'
    },
    {
        'source': 'fhlb-dallas', 'bank': 'Federal Home Loan Bank of Dallas',
        'id': 'fhlb-dallas-sbb', 'opp': 'FHLBD-SBB',
        'name': 'Small Business Boost (SBB)',
        'desc': 'Secondary unsecured loan to fill financing gaps for small businesses. Max $125,000 or 50% of member loan.',
        'elig': 'Small businesses meeting job requirements (1 job per $62,500).',
        'min': 10000, 'max': 125000,
        'open': '2026-01-01', 'close': '2026-12-31',
        'type': 'loan', 'category': 'small_business',
        'url': 'https://www.fhlb.com/community-programs/small-business-and-economic-development-programs/small-business-boost'
    },
    {
        'source': 'fhlb-dallas', 'bank': 'Federal Home Loan Bank of Dallas',
        'id': 'fhlb-dallas-drp', 'opp': 'FHLBD-DRP',
        'name': 'Disaster Relief Program (DRP)',
        'desc': 'Favorably priced advances for recovery in FEMA-declared disaster areas. Year-round.',
        'elig': 'Individuals and businesses in declared disaster areas apply through FHLB member institutions.',
        'min': 10000, 'max': 250000,
        'open': '2026-01-01', 'close': '2026-12-31',
        'type': 'loan', 'category': 'disaster_recovery',
        'url': 'https://www.fhlb.com/community-programs/disaster-recovery-assistance-programs'
    },
    # ── FHLB Atlanta (adjacent — useful for AL, FL, GA, NC, SC partnerships) ──
    {
        'source': 'fhlb-atlanta', 'bank': 'Federal Home Loan Bank of Atlanta',
        'id': 'fhlb-atlanta-ahp-general', 'opp': 'FHLBA-AHP-GEN',
        'name': 'AHP General Fund',
        'desc': 'Competitive grant for acquisition, construction, or rehabilitation of affordable housing. Up to $1M per project.',
        'elig': 'Housing authorities, nonprofits, developers in FHLB Atlanta district (AL, FL, GA, NC, SC, VA, WV).',
        'min': 50000, 'max': 1000000,
        'open': '2026-03-15', 'close': '2026-05-07',
        'type': 'competitive', 'category': 'affordable_housing',
        'url': 'https://corp.fhlbatl.com/services/affordable-housing-programs/'
    },
    {
        'source': 'fhlb-atlanta', 'bank': 'Federal Home Loan Bank of Atlanta',
        'id': 'fhlb-atlanta-first-homebuyer', 'opp': 'FHLBA-FTHB',
        'name': 'First-Time Homebuyer Product',
        'desc': 'Down payment and closing costs assistance for first-time homebuyers. Up to $17,500.',
        'elig': 'First-time homebuyers using FHLB Atlanta member lender.',
        'min': 1000, 'max': 17500,
        'open': '2026-01-01', 'close': '2026-12-31',
        'type': 'downpayment', 'category': 'homeownership',
        'url': 'https://corp.fhlbatl.com/services/affordable-housing-programs/homebuyers-and-homeowners/'
    },
    {
        'source': 'fhlb-atlanta', 'bank': 'Federal Home Loan Bank of Atlanta',
        'id': 'fhlb-atlanta-community-partners', 'opp': 'FHLBA-COMM-PARTNERS',
        'name': 'Community Partners Product',
        'desc': 'Down payment assistance for critical profession workers. Up to $20,000 for law enforcement, educators, health care workers, firefighters, veterans.',
        'elig': 'Critical profession workers using FHLB Atlanta member lender.',
        'min': 5000, 'max': 20000,
        'open': '2026-01-01', 'close': '2026-12-31',
        'type': 'downpayment', 'category': 'workforce_housing',
        'url': 'https://corp.fhlbatl.com/services/affordable-housing-programs/homebuyers-and-homeowners/'
    },
    {
        'source': 'fhlb-atlanta', 'bank': 'Federal Home Loan Bank of Atlanta',
        'id': 'fhlb-atlanta-rebuild', 'opp': 'FHLBA-REBUILD',
        'name': 'Community Rebuild and Restore Product',
        'desc': 'Rehabilitation assistance for homes in FEMA-designated disaster areas. Up to $25,000.',
        'elig': 'Homeowners in FEMA-declared disaster areas in FHLB Atlanta district.',
        'min': 5000, 'max': 25000,
        'open': '2026-01-01', 'close': '2026-12-31',
        'type': 'disaster', 'category': 'disaster_recovery',
        'url': 'https://corp.fhlbatl.com/services/affordable-housing-programs/homebuyers-and-homeowners/'
    },
    {
        'source': 'fhlb-atlanta', 'bank': 'Federal Home Loan Bank of Atlanta',
        'id': 'fhlb-atlanta-workforce', 'opp': 'FHLBA-WORKFORCE',
        'name': 'Workforce Housing Plus+ Program',
        'desc': 'Down payment and closing cost assistance for workforce housing. Up to $15,000 per homeowner. $20M total allocation.',
        'elig': 'Homebuyers between 80.01% and 120% of AMI using FHLB Atlanta member lender.',
        'min': 5000, 'max': 15000,
        'open': '2026-01-01', 'close': '2026-12-31',
        'type': 'downpayment', 'category': 'workforce_housing',
        'url': 'https://corp.fhlbatl.com/services/affordable-housing-programs/'
    },
]


def get_db():
    if not DB_URL:
        env_path2 = os.path.join(os.path.dirname(__file__), '..', '.env')
        if os.path.exists(env_path2):
            for line in open(env_path2):
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    k, _, v = line.partition('=')
                    if k.strip() == 'DATABASE_URL':
                        DB_URL = v.strip()
    p = urllib.parse.urlparse(DB_URL)
    pw = urllib.parse.unquote(p.password) if '%' in p.password else p.password
    return psycopg2.connect(
        host=p.hostname, port=p.port or 5432, dbname=p.path[1:],
        user=p.username, password=pw
    )


def upsert(conn, prog, year):
    today = datetime.now().strftime('%Y-%m-%d')
    close_dt = prog['close'].replace('2026', str(year))
    open_dt = prog['open'].replace('2026', str(year))
    status = 'closed' if close_dt < today else ('posted' if open_dt <= today else 'forecasted')
    grant_key = f"{prog['opp']}-{year}::{status}"

    c = conn.cursor()
    c.execute("""
        INSERT INTO grants_catalog (
            id, opportunity_number, title, agency, description, eligibility,
            amount_min, amount_max, open_date, close_date,
            grant_type, source, status, url, category, grant_key
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (grant_key) DO UPDATE SET
            title = EXCLUDED.title, description = EXCLUDED.description,
            close_date = EXCLUDED.close_date, status = EXCLUDED.status,
            amount_min = EXCLUDED.amount_min, amount_max = EXCLUDED.amount_max,
            updated_at = now()
    """, (
        f"{prog['id']}-{year}",
        f"{prog['opp']}-{year}",
        f"{prog['name']} ({year})",
        prog['bank'],
        prog['desc'], prog['elig'],
        prog['min'], prog['max'],
        open_dt, close_dt,
        prog['type'], prog['source'], status,
        prog['url'], prog['category'],
        grant_key
    ))
    conn.commit()
    print(f"  {prog['bank']} | {prog['name']} ({year}): {status}")


def main():
    print("=== FHLB Grant Sync: Dallas + Atlanta ===")
    conn = get_db()
    year = datetime.now().year
    for prog in PROGRAMS:
        for yr in [year, year+1]:
            upsert(conn, prog, yr)
    conn.close()
    print("\n=== Done ===")


if __name__ == '__main__':
    main()
