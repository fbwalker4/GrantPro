#!/usr/bin/env python3
"""Smart Grant Matcher -- matches project descriptions to grants using AI."""

import json
import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger('grantpro.matcher')


def match_grants(project_description: str, org_profile: Dict = None, state: str = None, limit: int = 10) -> List[Dict]:
    """Match a project description against the grant catalog using Gemini AI.

    Takes the user's project description + org profile and asks Gemini to
    score and rank grants from the catalog by relevance and eligibility.

    Returns list of {grant_id, title, agency, score, match_reasons, missing_requirements, match_notes}
    """
    from db_connection import get_connection

    # Load all active grants from catalog
    conn = get_connection()
    c = conn.cursor()
    c.execute("""SELECT id, title, agency, agency_code, category,
                 amount_min, amount_max, description, eligibility,
                 template, close_date, url
                 FROM grants_catalog
                 WHERE status = 'active'
                 ORDER BY title""")
    grants = [dict(row) if hasattr(row, 'keys') else dict(zip([d[0] for d in c.description], row)) for row in c.fetchall()]
    conn.close()

    if not grants:
        return []

    # Build org context
    org_context = ""
    if org_profile:
        org_details = org_profile.get('organization_details') or {}
        org_prof = org_profile.get('organization_profile') or {}
        focus = org_profile.get('focus_areas') or []
        past = org_profile.get('past_grants') or []

        org_context = f"""
APPLICANT PROFILE:
- Organization type: {org_details.get('organization_type') or org_prof.get('organization_type', 'Unknown')}
- State: {state or org_details.get('state', 'Unknown')}
- EIN: {'Yes' if org_details.get('ein') else 'No'}
- UEI: {'Yes' if org_details.get('uei') else 'No'}
- SAM.gov: {'Active' if org_details.get('sam_gov_status') == 'active' else 'Unknown'}
- Focus areas: {', '.join(focus) if focus else 'Not specified'}
- Past grants: {'; '.join(f"{p.get('grant_name','')} from {p.get('funding_organization','')} (${p.get('amount_received',0):,})" for p in past[:5]) if past else 'None listed'}
- Annual revenue: {org_prof.get('annual_revenue', 'Unknown')}
- Employees: {org_prof.get('employees', 'Unknown')}
"""

    # Build grants summary for AI (truncate to fit context)
    grants_text = ""
    for i, g in enumerate(grants[:50]):  # Limit to 50 grants for context window
        grants_text += f"""
GRANT #{i+1}: {g.get('id','')}
Title: {g.get('title','')}
Agency: {g.get('agency','')}
Category: {g.get('category','')}
Amount: ${g.get('amount_min',0):,} - ${g.get('amount_max',0):,}
Eligibility: {(g.get('eligibility','') or '')[:200]}
Description: {(g.get('description','') or '')[:300]}
Deadline: {g.get('close_date','Unknown')}
"""

    prompt = f"""You are a federal grants eligibility analyst. A user has described their project. Match it against the available grants and return the best matches.

PROJECT DESCRIPTION:
{project_description}

{org_context}

AVAILABLE GRANTS:
{grants_text}

INSTRUCTIONS:
For each grant that is a potential match (up to {limit} grants), return a JSON array with this structure:
[
  {{
    "grant_id": "the grant ID exactly as shown above",
    "score": 85,
    "match_reasons": ["reason 1 why this is a good match", "reason 2"],
    "missing_requirements": ["requirement the applicant may not meet"],
    "match_notes": "Brief note about match/cost share if applicable"
  }}
]

SCORING RULES:
- 90-100: Excellent match. Project directly aligns with grant purpose, org is clearly eligible.
- 70-89: Good match. Project aligns well but may need some adaptation or the org may be missing minor requirements.
- 50-69: Possible match. Some alignment but significant gaps in eligibility or project fit.
- Below 50: Don't include.

Only include grants scoring 50 or above. Sort by score descending.
Return ONLY valid JSON array. No explanations outside the JSON."""

    try:
        from google import genai
        import re

        api_key = os.environ.get('GP_GOOGLE_API_KEY') or os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            env_path = os.path.expanduser('~/.hermes/grant-system/.env')
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        if line.startswith('GP_GOOGLE_API_KEY='):
                            api_key = line.split('=', 1)[1].strip()

        if not api_key:
            logger.error("No Google API key for grant matching")
            return []

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )

        raw = response.text.strip()
        if raw.startswith('```'):
            raw = re.sub(r'^```(?:json)?\n?', '', raw)
            raw = re.sub(r'\n?```$', '', raw)

        matches = json.loads(raw)

        # Enrich with grant details from catalog
        grants_by_id = {g['id']: g for g in grants}
        enriched = []
        for m in matches:
            grant = grants_by_id.get(m.get('grant_id'))
            if grant:
                enriched.append({
                    **m,
                    'title': grant.get('title', ''),
                    'agency': grant.get('agency', ''),
                    'amount_min': grant.get('amount_min', 0),
                    'amount_max': grant.get('amount_max', 0),
                    'category': grant.get('category', ''),
                    'close_date': grant.get('close_date', ''),
                    'description': (grant.get('description', '') or '')[:200],
                })

        return enriched[:limit]

    except json.JSONDecodeError as e:
        logger.error(f"AI returned invalid JSON for matching: {e}")
        return []
    except Exception as e:
        logger.error(f"Grant matching failed: {e}")
        return []
