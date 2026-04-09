# Vercel Cron: /api/cron/fhlb-sync
# Schedule: weekly (Mondays 6am UTC)
# Trigger: GET /api/cron/fhlb-sync?key=<CRON_SECRET>
"""
FHLB Dallas Grant Sync — Vercel Cron Endpoint
Runs every Monday at 6am UTC.
Scrapes FHLB Dallas website and upserts grants to Supabase.
"""
import json, os, sys, requests, re, psycopg2, urllib.parse
from datetime import datetime

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; GrantProBot/1.)'}
PROGRAMS = [
    {'id': 'fhlb-dallas-ahp-general', 'name': 'AHP General Fund',
     'agency': 'Federal Home Loan Bank of Dallas',
     'url': 'https://www.fhlb.com/community-programs/affordable-housing-program-general-fund',
     'grant_type': 'competitive'},
    {'id': 'fhlb-dallas-help', 'name': 'HELP Down Payment Assistance',
     'agency': 'Federal Home Loan Bank of Dallas',
     'url': 'https://www.fhlb.com/community-programs/homeownership-programs/down-payment-and-closing-cost-assistance-help',
     'grant_type': 'downpayment'},
    {'id': 'fhlb-dallas-snap', 'name': 'SNAP Special Needs Assistance',
     'agency': 'Federal Home Loan Bank of Dallas',
     'url': 'https://www.fhlb.com/community-programs/homeownership-programs/special-needs-assistance-program-snap',
     'grant_type': 'special_needs'},
    {'id': 'fhlb-dallas-dra', 'name': 'DRA Disaster Rebuilding Assistance',
     'agency': 'Federal Home Loan Bank of Dallas',
     'url': 'https://www.fhlb.com/community-programs/homeownership-programs/disaster-rebuilding-assistance',
     'grant_type': 'disaster'},
]

def get_db():
    pw = urllib.parse.unquote(os.environ.get('DATABASE_URL','').split(':')[-1].split('@')[0].replace('%21','!'))
    return psycopg2.connect(
        host=os.environ.get('PGHOST','aws-1-us-east-1.pooler.supabase.com'),
        port=int(os.environ.get('PGPORT',6543)),
        dbname=os.environ.get('PGDATABASE','postgres'),
        user=os.environ.get('PGUSER','postgres.mubghncbtnkjkywbcfts'),
        password=pw
    )

def scrape(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200: return ''
        html = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.S)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.S)
        return re.sub(r'<[^>]+>', ' ', html)
    except: return ''

def window_dates(text):
    m = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})\s+through\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})', text)
    if m:
        try:
            od = datetime.strptime(m.group(1).replace(',',''), '%B %d %Y').strftime('%Y-%m-%d')
            cd = datetime.strptime(m.group(2).replace(',',''), '%B %d %Y').strftime('%Y-%m-%d')
            return od, cd
        except: return '', ''
    return '', ''

def upsert(g):
    conn = get_db(); c = conn.cursor(); now = datetime.now().isoformat()
    try:
        c.execute("""INSERT INTO grants_catalog
            (id, opportunity_number, title, agency, description, eligibility, amount_min, amount_max,
             open_date, close_date, grant_type, source, status, created_at, updated_at, url)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET
                title=EXCLUDED.title, description=EXCLUDED.description,
                close_date=EXCLUDED.close_date, status=EXCLUDED.status, updated_at=EXCLUDED.updated_at""",
            (g['id'], g.get('opp',''), g['title'], g['agency'], g.get('desc',''), g.get('elig',''),
             g.get('min',10000), g.get('max',500000), g.get('open',''), g['close'],
             g['grant_type'], 'fhlb-dallas', g['status'], now, now, g['url']))
        conn.commit()
    finally:
        conn.close()

def handler(event, context):
    # Verify cron secret
    secret = os.environ.get('CRON_SECRET','')
    if secret and event.get('query',{}).get('key') != secret:
        return {'statusCode': 401, 'body': json.dumps({'error': 'unauthorized'})}

    year = datetime.now().year
    results = []
    for prog in PROGRAMS:
        for yr in [year, year+1]:
            text = scrape(prog['url'])
            today = datetime.now().strftime('%Y-%m-%d')
            open_d, close_d = window_dates(text) if text else ('', '')
            deadline = close_d or f'{yr}-04-30'
            open_dt = open_d or f'{yr}-01-01'
            status = 'closed' if deadline < today else ('posted' if open_dt <= today else 'forecasted')
            amt_min = 1000 if 'down payment' in prog['name'].lower() else 10000
            amt_max = 25000 if 'down payment' in prog['name'].lower() else 500000
            desc = text[:2000] if text else f"FHLB Dallas {prog['name']}."
            elig = 'Housing authorities, nonprofits, developers in FHLB Dallas district (AL, AR, LA, MS, TX). Must be FHLB member.'
            g = {'id': f"{prog['id']}-{yr}", 'opp': f"FHLBD-{prog['id'].split('-')[-1].upper()}-{yr}",
                 'title': f"{prog['name']} ({yr})", 'agency': prog['agency'],
                 'desc': desc[:2000], 'elig': elig,
                 'min': amt_min, 'max': amt_max, 'open': open_dt, 'close': deadline,
                 'grant_type': prog['grant_type'], 'status': status, 'url': prog['url']}
            upsert(g)
            results.append({'id': g['id'], 'status': status})
    return {'statusCode': 200, 'body': json.dumps({'ok': True, 'synced': results})}
