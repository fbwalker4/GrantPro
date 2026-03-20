#!/usr/bin/env python3
"""Test AI generation with organization data"""
import os
import json
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

if not api_key:
    print("ERROR: No valid API key found")
    exit(1)

# Simulate the prompt that would be sent for a grant section
# Using the same prompt structure as in app.py

grant_name = "Smart and Connected Communities"
agency = "National Science Foundation"
org_name = "Test Client"
section_name = "Project Summary"
section_guidance = "Must contain: (1) a statement of the project activity, (2) an explicit statement of the intellectual merit, and (3) a statement of the broader impacts."

# Test 1: WITHOUT organization data (what currently happens)
prompt_no_org = f"""You are an expert grant writer with 20+ years of experience writing successful federal grants. 

Generate high-quality, professional grant content for the following section.

**Grant Details:**
- Grant Name: {grant_name}
- Funding Agency: {agency}
- Applicant Organization: {org_name}

**Section Details:**
- Section Name: {section_name}
- Requirements: {section_guidance}

Please write compelling, specific, and competitive grant content that:
1. Directly addresses the agency's requirements
2. Uses strong, active voice
3. Includes specific details and examples
4. Aligns with the agency's priorities and mission
5. Is ready to submit (not a placeholder)

Write the complete section content now:"""

print("=" * 60)
print("TEST 1: WITHOUT organization data (mission, description, etc.)")
print("=" * 60)

client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=prompt_no_org
)
print(response.text[:1000])
print("\n")

# Test 2: WITH organization data
prompt_with_org = f"""You are an expert grant writer with 20+ years of experience writing successful federal grants. 

Generate high-quality, professional grant content for the following section.

**Grant Details:**
- Grant Name: {grant_name}
- Funding Agency: {agency}
- Applicant Organization: {org_name}

**Section Details:**
- Section Name: {section_name}
- Requirements: {section_guidance}

Organization Mission: We are a community development organization serving low-income families through after-school programs, job training, and affordable housing initiatives.

Organization Description: Founded in 1995, we operate 5 community centers in the Gulf Coast region and have successfully completed 50+ federal grants totaling $10M in funding.

Please write compelling, specific, and competitive grant content that:
1. Directly addresses the agency's requirements
2. Uses strong, active voice
3. Includes specific details and examples about the actual organization
4. Aligns with the agency's priorities and mission
5. Is ready to submit (not a placeholder)

Write the complete section content now:"""

print("=" * 60)
print("TEST 2: WITH organization data (mission, description)")
print("=" * 60)

response2 = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=prompt_with_org
)
print(response2.text[:1000])
