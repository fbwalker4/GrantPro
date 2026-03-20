#!/usr/bin/env python3
import json
with open('/Users/fbwalker4/.hermes/grant-system/templates/agency_templates.json') as f:
    data = json.load(f)

# Check structure
agencies = data['agencies']
nsf = agencies.get('nsf', {})
print("NSF template keys:", nsf.keys())
print("NSF template:", json.dumps(nsf, indent=2)[:1000])
