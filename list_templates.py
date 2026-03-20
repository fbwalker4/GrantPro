#!/usr/bin/env python3
import json

# Load templates
with open('/Users/fbwalker4/.hermes/grant-system/templates/agency_templates.json') as f:
    data = json.load(f)

agencies = data['agencies']
print("=== TEMPLATES ===")
for agency, info in agencies.items():
    sections = info.get('sections', [])
    print(f"{agency}: {len(sections)} sections")
    for s in sections[:3]:
        print(f"  - {s.get('name', s.get('id'))}")
    if len(sections) > 3:
        print(f"  ... and {len(sections)-3} more")
