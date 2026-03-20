#!/usr/bin/env python3
"""
Fast test of AI generation - minimal prompts
"""
import json
import sqlite3
import os
from google import genai

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

print(f"Testing with: {org_name}")

ai = genai.Client(api_key=api_key)

# Test just one section from a few templates
tests = [
    ('nsf', 'project_summary', 'Project Summary', 'Must contain statement of project activity, intellectual merit, and broader impacts'),
    ('hud', 'need_statement', 'Need Statement', 'Describe the need for the project'),
    ('doe', 'project_summary', 'Project Summary', 'Describe project objectives and methods'),
]

results = []

for agency_key, section_id, section_name, guidance in tests:
    print(f"\n=== {agency_key.upper()} - {section_id} ===")
    
    prompt = f"""Write a {section_name} for {agency_key.upper()} grant.
Org: {org_name}
Mission: {intake_data.get('mission', '')[:100]}
Requirements: {guidance}

Write now:"""
    
    try:
        response = ai.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        content = response.text
        length = len(content)
        
        # Check for placeholders
        has_placeholder = any(p in content.lower() for p in ['test client', '[specific', '[your'])
        
        print(f"Length: {length} chars")
        print(f"Has placeholder: {has_placeholder}")
        print(f"Content: {content[:300]}...")
        
        results.append({'template': agency_key, 'section': section_id, 'success': True, 'has_placeholder': has_placeholder})
        
    except Exception as e:
        print(f"ERROR: {e}")
        results.append({'template': agency_key, 'section': section_id, 'success': False, 'error': str(e)})

print("\n" + "=" * 50)
print("RESULTS:")
for r in results:
    status = "✅" if r.get('success') else "❌"
    placeholder = "⚠️" if r.get('has_placeholder') else ""
    print(f"  {status} {r['template']}/{r['section']} {placeholder}")
