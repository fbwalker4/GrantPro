#!/usr/bin/env python3
"""Get template sections."""
import sys, os
sys.path.insert(0, '/Users/fbwalker4/.hermes/grant-system')
os.chdir('/Users/fbwalker4/.hermes/grant-system')
from research.grant_researcher import GrantResearcher
gr = GrantResearcher()

for tmpl in ['fhlb', 'hud', 'generic', 'nsf', 'doe']:
    sections = gr.get_template_sections(tmpl)
    if sections:
        print(f"\n{tmpl} ({len(sections)} sections):")
        for s in sections:
            print(f"  - {s.get('id')}: {s.get('name')}")
