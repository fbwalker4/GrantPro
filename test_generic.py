#!/usr/bin/env python3
"""Test specific sections that had issues"""
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
print(f"Mission: {intake_data.get('mission', 'N/A')[:60]}...")

ai = genai.Client(api_key=api_key)

# Test generic project_summary
prompt = f"""Write a project summary for a grant application.
Org: {org_name}
Mission: {intake_data.get('mission', '')[:80]}
Budget: {json.dumps(intake_data.get('budget_info', {}))[:100]}
Write now:"""

response = ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
content = response.text
print(f"\nGeneric project_summary ({len(content)} chars):")
print(content[:500])

# Check for actual placeholders (not just the org name)
has_placeholder = any(p in content.lower() for p in ['[specific', 'test client', '[your organization'])
print(f"Has placeholder: {has_placeholder}")
