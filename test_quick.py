#!/usr/bin/env python3
"""
Quick test of AI generation - just a few key templates
"""
import json
import sqlite3
import os
from google import genai

# Connect to database
conn = sqlite3.connect('/Users/fbwalker4/.hermes/grant-system/tracking/grants.db')
cursor = conn.cursor()

# Get test client
cursor.execute("SELECT id, organization_name, intake_data FROM clients WHERE id = 'client-hermes-001'")
client = cursor.fetchone()
org_name = client[1]
intake_data = json.loads(client[2]) if client[2] else {}

print(f"Testing with: {org_name}")
print(f"Mission: {intake_data.get('mission', 'N/A')[:80]}...")
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
    print("ERROR: No API key")
    exit(1)

ai = genai.Client(api_key=api_key)

# Test a few key templates
test_templates = ['nsf', 'hud', 'doe', 'epa']
results = []

for agency_key in test_templates:
    print(f"=== Testing {agency_key.upper()} ===")
    
    # Load template
    with open('/Users/fbwalker4/.hermes/grant-system/templates/agency_templates.json') as f:
        templates_data = json.load(f)
    
    agency = templates_data['agencies'].get(agency_key, {})
    sections = agency.get('required_sections', [])[:2]  # Just first 2 sections
    
    for section in sections:
        section_id = section.get('id')
        section_name = section.get('name')
        guidance = section.get('guidance', '')
        
        prompt = f"""Write a {section_name} section for a grant application.

Agency: {agency.get('full_name')}
Organization: {org_name}
Mission: {intake_data.get('mission')}
Description: {intake_data.get('description')}

Requirements: {guidance}

Write the section now:"""
        
        try:
            response = ai.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            content = response.text
            length = len(content)
            
            # Check for placeholders
            has_placeholder = any(p in content.lower() for p in ['[specific', 'test client', 'your organization'])
            
            results.append({
                'template': agency_key,
                'section': section_id,
                'success': True,
                'length': length,
                'has_placeholder': has_placeholder
            })
            
            status = "❌ PLACEHOLDER" if has_placeholder else "✅ OK"
            print(f"  {section_id}: {length} chars {status}")
            
            # Print first 200 chars to verify content
            print(f"    Preview: {content[:200]}...")
            print()
            
        except Exception as e:
            results.append({
                'template': agency_key,
                'section': section_id,
                'success': False,
                'error': str(e)
            })
            print(f"  {section_id}: ERROR - {str(e)[:50]}")
            print()

print("=" * 50)
print("SUMMARY:")
successes = [r for r in results if r.get('success')]
failures = [r for r in results if not r.get('success')]
placeholders = [r for r in results if r.get('has_placeholder')]
print(f"  Total: {len(results)}")
print(f"  Success: {len(successes)}")
print(f"  Failed: {len(failures)}")
print(f"  Has placeholders: {len(placeholders)}")

conn.close()
