#!/usr/bin/env python3
"""
NOFO Parser for GrantPro
Fetches and parses actual NOFO/FOA documents from Grants.gov
to extract grant-specific requirements.
"""

import json
import os
import re
import secrets
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import requests

from db_connection import get_connection

logger = logging.getLogger('grantpro.nofo')

# Grants.gov API endpoints
GRANTS_GOV_SEARCH = "https://api.grants.gov/v1/api/search2"
GRANTS_GOV_FETCH = "https://api.grants.gov/v1/api/fetchOpportunity"
GRANTS_GOV_DOWNLOAD = "https://apply07.grants.gov/grantsws/rest/opportunity/att/download"

# Local storage for downloaded NOFOs
NOFO_DIR = Path.home() / '.hermes' / 'grant-system' / 'data' / 'nofos'


def search_opportunity(opp_number: str) -> Optional[Dict]:
    """Search Grants.gov for an opportunity by number. Returns opportunity hit or None."""
    try:
        resp = requests.post(GRANTS_GOV_SEARCH, json={
            "oppNum": opp_number,
            "rows": 5,
            "oppStatuses": "forecasted|posted|closed|archived"
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        hits = data.get("oppHits", [])
        if hits:
            return hits[0]
        return None
    except Exception as e:
        logger.error(f"Grants.gov search failed for {opp_number}: {e}")
        return None


def fetch_opportunity_details(opp_id: int) -> Optional[Dict]:
    """Fetch full opportunity details including attachments."""
    try:
        resp = requests.post(GRANTS_GOV_FETCH, json={
            "opportunityId": opp_id
        }, timeout=15)
        resp.raise_for_status()
        return resp.json().get("data", {})
    except Exception as e:
        logger.error(f"Grants.gov fetch failed for {opp_id}: {e}")
        return None


def find_nofo_attachment(details: Dict) -> Optional[Dict]:
    """Find the primary NOFO document from the attachment list.
    Prioritizes: PDF > DOCX, and filenames/descriptions containing NOFO/FOA/announcement."""
    attachments = []
    for folder in details.get("synopsisAttachmentFolders", []):
        for att in folder.get("synopsisAttachments", []):
            attachments.append({
                "id": att["id"],
                "fileName": att.get("fileName", ""),
                "mimeType": att.get("mimeType", ""),
                "fileSize": att.get("fileLobSize", 0),
                "description": att.get("fileDescription", ""),
                "folderType": folder.get("folderType", ""),
            })

    if not attachments:
        return None

    # Score attachments to find the NOFO
    def score(att):
        s = 0
        name_lower = (att["fileName"] + " " + att["description"]).lower()
        # Prefer files with NOFO-related keywords
        for kw in ["nofo", "notice of funding", "full announcement", "funding opportunity", "foa", "solicitation", "program announcement"]:
            if kw in name_lower:
                s += 10
        # Prefer PDFs
        if "pdf" in att["mimeType"].lower() or att["fileName"].lower().endswith(".pdf"):
            s += 5
        # Prefer larger files (more likely to be the full NOFO)
        if att["fileSize"] > 100000:  # > 100KB
            s += 3
        if att["fileSize"] > 500000:  # > 500KB
            s += 2
        # Deprioritize amendments, forms, instructions
        for neg in ["amendment", "sf-424", "form", "errata", "correction", "faq"]:
            if neg in name_lower:
                s -= 5
        return s

    attachments.sort(key=score, reverse=True)
    return attachments[0] if attachments else None


def download_nofo(attachment_id: int, filename: str, opp_number: str) -> Optional[Path]:
    """Download a NOFO attachment to local storage."""
    NOFO_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r'[^\w\-.]', '_', filename)
    local_path = NOFO_DIR / f"{opp_number}_{safe_name}"

    if local_path.exists():
        logger.info(f"NOFO already downloaded: {local_path}")
        return local_path

    try:
        resp = requests.get(f"{GRANTS_GOV_DOWNLOAD}/{attachment_id}", stream=True, timeout=60)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"Downloaded NOFO: {local_path} ({local_path.stat().st_size} bytes)")
        return local_path
    except Exception as e:
        logger.error(f"NOFO download failed: {e}")
        return None


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF file."""
    try:
        # Try pdfplumber first (best quality)
        import pdfplumber
        text_parts = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n\n".join(text_parts)
    except ImportError:
        pass

    try:
        # Fallback: PyPDF2 / pypdf
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n\n".join(text_parts)
    except ImportError:
        pass

    try:
        # Fallback: pdftotext CLI
        import subprocess
        result = subprocess.run(["pdftotext", str(pdf_path), "-"], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass

    return ""


def extract_text_from_docx(docx_path: Path) -> str:
    """Extract text from a DOCX file."""
    try:
        from docx import Document
        doc = Document(str(docx_path))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        return ""


def extract_nofo_text(file_path: Path) -> str:
    """Extract text from a NOFO file (PDF or DOCX)."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    elif suffix in (".docx", ".doc"):
        return extract_text_from_docx(file_path)
    else:
        # Try reading as text
        try:
            return file_path.read_text(errors="ignore")
        except Exception:
            return ""


def parse_nofo_with_ai(nofo_text: str, grant_name: str, agency: str) -> Dict:
    """Use Gemini AI to extract structured requirements from NOFO text.

    Returns a dict with: required_sections, evaluation_criteria, eligibility_rules,
    compliance_requirements, submission_instructions, match_requirements,
    page_limits, formatting_rules
    """
    # Truncate to ~100K chars to stay within model limits
    truncated = nofo_text[:100000]

    prompt = f"""You are a federal grants compliance analyst. Extract the structured requirements from this NOFO (Notice of Funding Opportunity).

NOFO for: {grant_name}
Agency: {agency}

EXTRACT THE FOLLOWING (return as valid JSON only, no markdown):

{{
  "required_sections": [
    {{
      "id": "snake_case_id",
      "name": "Section Display Name",
      "guidance": "Exact requirements from the NOFO for this section",
      "max_pages": null or number,
      "max_chars": null or number,
      "required": true or false,
      "components": ["list", "of", "required", "subcomponents"]
    }}
  ],
  "evaluation_criteria": [
    {{
      "criterion": "Name",
      "weight": "X points or X%",
      "description": "What reviewers will evaluate"
    }}
  ],
  "eligibility_rules": ["list of who can apply and restrictions"],
  "compliance_requirements": ["list of federal compliance requirements mentioned (Davis-Bacon, NEPA, Section 3, etc.)"],
  "submission_instructions": {{
    "portal": "Grants.gov or other",
    "deadline": "date and time",
    "format": "PDF, Word, etc.",
    "page_limit_total": null or number,
    "required_forms": ["SF-424", "SF-424A", etc.]
  }},
  "match_requirements": {{
    "required": true or false,
    "ratio": "e.g. 1:1 or 25%",
    "type": "cash, in-kind, or both",
    "amount_or_percentage": "specific amount or percentage"
  }},
  "page_limits": {{
    "total_narrative": null or number,
    "per_section": {{}}
  }},
  "formatting_rules": {{
    "font": "required font or null",
    "font_size": "required size or null",
    "line_spacing": "single, 1.5, or double or null",
    "margins": "required margins or null"
  }}
}}

IMPORTANT:
- Extract ONLY what the NOFO actually says. Do not invent requirements.
- If the NOFO does not specify something, use null.
- For required_sections, map EVERY section the NOFO requires applicants to write.
- Include the EXACT guidance text from the NOFO for each section.
- For evaluation_criteria, include the exact point values or percentages if specified.

NOFO TEXT:
{truncated}

Return ONLY valid JSON. No explanations, no markdown fences."""

    try:
        from core.ai_provider import generate_text, safe_json_loads, AIProviderError
        result = generate_text(prompt, model='gemini-2.5-flash')
        raw_response = result.text.strip()

        if raw_response.startswith("```"):
            raw_response = re.sub(r'^```(?:json)?\n?', '', raw_response)
            raw_response = re.sub(r'\n?```$', '', raw_response)

        parsed = safe_json_loads(raw_response)
        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"AI returned invalid JSON: {e}")
        return {"error": f"JSON parse error: {str(e)}", "raw": raw_response[:500]}
    except Exception as e:
        logger.error(f"AI NOFO parsing failed: {e}")
        return {"error": str(e)}


def fetch_and_parse_nofo(opportunity_number: str, grant_id: str, user_id: str, grant_name: str = "", agency: str = "") -> Dict:
    """Full pipeline: search -> fetch -> download -> extract -> parse -> store.

    Returns the parsed requirements dict, or {"error": "message"} on failure.
    """
    now = datetime.now().isoformat()
    req_id = f"req-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"

    # Step 1: Search Grants.gov
    logger.info(f"Searching Grants.gov for {opportunity_number}")
    hit = search_opportunity(opportunity_number)
    if not hit:
        return {"error": f"Opportunity {opportunity_number} not found on Grants.gov"}

    opp_id = int(hit["id"])

    # Step 2: Fetch details
    logger.info(f"Fetching opportunity {opp_id}")
    details = fetch_opportunity_details(opp_id)
    if not details:
        return {"error": f"Could not fetch opportunity details for {opp_id}"}

    # Step 3: Find and download NOFO
    attachment = find_nofo_attachment(details)
    nofo_text = ""
    nofo_file_path = ""
    nofo_source_url = ""

    if attachment:
        logger.info(f"Downloading NOFO: {attachment['fileName']}")
        nofo_source_url = f"{GRANTS_GOV_DOWNLOAD}/{attachment['id']}"
        local_path = download_nofo(attachment["id"], attachment["fileName"], opportunity_number)
        if local_path:
            nofo_file_path = str(local_path)
            nofo_text = extract_nofo_text(local_path)
            logger.info(f"Extracted {len(nofo_text)} chars from NOFO")

    # Fallback: use synopsis text if no attachment found
    if not nofo_text:
        synopsis = details.get("synopsisDesc", "")
        if synopsis:
            # Strip HTML tags
            nofo_text = re.sub(r'<[^>]+>', '', synopsis)
            logger.info(f"Using synopsis text ({len(nofo_text)} chars)")

    if not nofo_text:
        return {"error": "Could not extract any text from the NOFO document"}

    # Step 4: AI extraction
    logger.info("Parsing NOFO with AI...")
    parsed = parse_nofo_with_ai(nofo_text, grant_name or hit.get("title", ""), agency or hit.get("agency", ""))

    if "error" in parsed:
        return parsed

    # Step 5: Store in database
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO grant_requirements
                    (id, grant_id, user_id, opportunity_number, nofo_source_url, nofo_file_path,
                     extraction_status, extracted_at,
                     required_sections, evaluation_criteria, eligibility_rules,
                     compliance_requirements, submission_instructions, match_requirements,
                     page_limits, formatting_rules, raw_nofo_text,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'complete', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (req_id, grant_id, user_id, opportunity_number, nofo_source_url, nofo_file_path,
                  now,
                  json.dumps(parsed.get("required_sections", [])),
                  json.dumps(parsed.get("evaluation_criteria", [])),
                  json.dumps(parsed.get("eligibility_rules", [])),
                  json.dumps(parsed.get("compliance_requirements", [])),
                  json.dumps(parsed.get("submission_instructions", {})),
                  json.dumps(parsed.get("match_requirements", {})),
                  json.dumps(parsed.get("page_limits", {})),
                  json.dumps(parsed.get("formatting_rules", {})),
                  nofo_text[:500000],  # Cap at 500K to avoid DB bloat
                  now, now))
        conn.commit()
        logger.info(f"Stored requirements: {req_id}")
    except Exception as e:
        logger.error(f"Failed to store requirements: {e}")
    finally:
        conn.close()

    parsed["_req_id"] = req_id
    parsed["_sections_count"] = len(parsed.get("required_sections", []))
    parsed["_nofo_chars"] = len(nofo_text)

    return parsed


def get_grant_requirements(grant_id: str) -> Optional[Dict]:
    """Load stored requirements for a grant application."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM grant_requirements WHERE grant_id = ? ORDER BY created_at DESC LIMIT 1', (grant_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return None

    r = dict(row) if hasattr(row, 'keys') else {}
    if not r:
        return None

    # Parse JSON fields
    for field in ['required_sections', 'evaluation_criteria', 'eligibility_rules',
                  'compliance_requirements', 'submission_instructions', 'match_requirements',
                  'page_limits', 'formatting_rules']:
        val = r.get(field)
        if val and isinstance(val, str):
            try:
                r[field] = json.loads(val)
            except json.JSONDecodeError:
                pass

    return r
