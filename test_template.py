#!/usr/bin/env python3
"""
Test all templates - runs one at a time to avoid timeouts
"""
import json
import sqlite3
import os
from google import genai
import sys

# Load API key
api_key = None
env_path = os.path.expanduser('~/.hermes/.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.startswith('GOOGLE_API_KEY='):
                api_key = line.split('=', 1)[1].strip()
                if api_key == '***' or not api_key:
                    api_key = None
                break

# Get client data
conn = sqlite3.connect('/Users/fbwalker4/.hermes/grant-system/tracking/grants.db')
cursor = conn.cursor()
cursor.execute("SELECT organization_name, intake_data FROM clients WHERE id = 'client-hermes-001'")
client = cursor.fetchone()
org_name = client[0]
intake_data = json.loads(client[1]) if client[1] else {}
conn.close()

# Load templates
with open('/Users/fbwalker4/.hermes/grant-system/templates/agency_templates.json') as f:
    templates_data = json.load(f)

agencies = templates_data['agencies']

ai = genai.Client(api_key=api_key)

# Get command line args for which template to test
template_to_test = sys.argv[1] if len(sys.argv) > 1 else None

results = []

if template_to_test:
    # Test specific template
    if template_to_test not in agencies:
        print(f"Template {template_to_test} not found")
        exit(1)
    
    agency = agencies[template_to_test]
    sections = agency.get('required_sections', [])
    
    print(f"=== Testing {template_to_test.upper()} ({len(sections)} sections) ===")
    
    for section in sections[:3]:  # Test first 3 sections
        section_id = section.get('id')
        section_name = section.get('name')
        guidance = section.get('guidance', '')[:200]
        
        prompt = f"""Write {section_name} for {agency.get('full_name')} grant.
Org: {org_name}
Mission: {intake_data.get('mission', '')[:80]}
Requirements: {guidance}
Write now:"""
        
        try:
            response = ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            content = response.text
            has_placeholder = any(p in content.lower() for p in ['test client', '[specific', '[your'])
            
            print(f"  {section_id}: {len(content)} chars {'⚠️ PLACEHOLDER' if has_placeholder else '✅'}")
            results.append({'section': section_id, 'success': True, 'has_placeholder': has_placeholder})
        except Exception as e:
            print(f"  {section_id}: ERROR - {str(e)[:50]}")
            results.append({'section': section_id, 'success': False, 'error': str(e)})
else:
    # List all templates
    print("Available templates:")
    for key, info in agencies.items():
        sections = len(info.get('required_sections', []))
        print(f"  {key}: {sections} sections")

print("\nDone")
