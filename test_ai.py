#!/usr/bin/env python3
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

if not api_key:
    print("ERROR: No valid API key found")
    exit(1)
else:
    print(f"API key found: {api_key[:10]}...")
    
    # Test the API
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents="Say 'Hello, AI is working!' in exactly 5 words."
    )
    print(f"Response: {response.text}")
