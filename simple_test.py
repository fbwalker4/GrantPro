#!/usr/bin/env python3
import os
from google import genai

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

print(f"API key available: {bool(api_key)}")

if api_key:
    print("Testing API call...")
    ai = genai.Client(api_key=api_key)
    response = ai.models.generate_content(
        model='gemini-2.5-flash',
        contents="Say 'test successful' in 3 words"
    )
    print(f"Response: {response.text}")
else:
    print("No API key")
