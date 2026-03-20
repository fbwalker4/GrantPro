#!/usr/bin/env python3
"""
Comprehensive test of AI generation for all template/grant combinations
"""
import json
import sqlite3
import os
from datetime import datetime
from google import genai

# Load config
with open('/Users/fbwalker4/.hermes/grant-system/templates/agency_templates.json') as f:
    templates_data = json.load(f)

agencies = templates_data['agencies']

# Connect to database
conn = sqlite3.connect('/Users/fbwalker4/.hermes/grant-system/tracking/grants.db')
cursor = conn.cursor()

# Get test client
cursor.execute("SELECT id, organization_name, intake_data FROM clients WHERE id = 'client-hermes-001'")
client = cursor.fetchone()
client_id = client[0]
org_name = client[1]
intake_data = json.loads(client[2]) if client[2] else {}

print(f"Testing with client: {org_name}")
print(f"Intake data: mission={bool(intake_data.get('mission'))}, description={bool(intake_data.get('description'))}")
print()

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

if not api_key:
    print("ERROR: No API key found")
    exit(1)

client_ai = genai.Client(api_key=api_key)

# Test each template
results = []
template_count = 0
section_count = 0

for agency_key, agency_info in agencies.items():
    required_sections = agency_info.get('required_sections', [])
    if not required_sections:
        continue
    
    template_count += 1
    print(f"=== {agency_key.upper()} ({len(required_sections)} sections) ===")
    
    for section in required_sections:
        section_id = section.get('id')
        section_name = section.get('name')
        section_guidance = section.get('guidance', '')
        max_chars = section.get('max_chars', 'N/A')
        
        section_count += 1
        
        # Build prompt
        prompt = f"""You are an expert grant writer with 20+ years of experience writing successful federal grants. 

Generate high-quality, professional grant content for the following section.

**Grant Details:**
- Grant Name: Smart and Connected Communities (SCC)
- Funding Agency: {agency_info.get('full_name', agency_key.upper())}
- Applicant Organization: {org_name}

**Section Details:**
- Section Name: {section_name}
- Requirements: {section_guidance}
- Character Limit: {max_chars}

Organization Mission: {intake_data.get('mission', 'N/A')}
Organization Description: {intake_data.get('description', 'N/A')}
Existing Programs: {intake_data.get('programs', 'N/A')}

Please write compelling, specific, and competitive grant content that:
1. Directly addresses the agency's requirements
2. Uses strong, active voice
3. Includes specific details about the Gulf Coast CDC organization
4. Aligns with the agency's priorities and mission
5. Is ready to submit (not a placeholder)

Write the complete section content now:"""

        try:
            # Call AI
            response = client_ai.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            
            content = response.text
            content_length = len(content)
            
            # Check for generic placeholders
            has_placeholder = any(placeholder in content.lower() for placeholder in 
                ['[specific', '[insert', 'placeholder', 'test client', 'your organization'])
            
            results.append({
                'template': agency_key,
                'section': section_id,
                'section_name': section_name,
                'length': content_length,
                'has_placeholder': has_placeholder,
                'success': True
            })
            
            status = "❌ PLACEHOLDER" if has_placeholder else "✅ OK"
            print(f"  {section_id}: {content_length} chars {status}")
            
        except Exception as e:
            results.append({
                'template': agency_key,
                'section': section_id,
                'section_name': section_name,
                'error': str(e),
                'success': False
            })
            print(f"  {section_id}: ERROR - {str(e)[:50]}")
    
    print()

print("=" * 60)
print(f"SUMMARY: {template_count} templates, {section_count} sections tested")
print("=" * 60)

# Count successes and failures
successes = [r for r in results if r.get('success')]
failures = [r for r in results if not r.get('success')]
placeholders = [r for r in results if r.get('has_placeholder')]

print(f"Successful: {len(successes)}")
print(f"Failed: {len(failures)}")
print(f"Has placeholders: {len(placeholders)}")

if placeholders:
    print("\nTemplates with placeholder issues:")
    for p in placeholders:
        print(f"  - {p['template']}/{p['section']}")

conn.close()
