#!/usr/bin/env python
"""Test script to verify Gemini API configuration"""
import os
import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Test 1: Check if .env file exists
env_file = Path(__file__).parent / '.env'
print(f"1. .env file exists: {env_file.exists()}")
if env_file.exists():
    print(f"   Path: {env_file}")

# Test 2: Load config and check values
from app.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE_URL, GEMINI_ENABLED

print(f"\n2. Config loaded from app.config:")
print(f"   GEMINI_API_KEY: {'✓ Set' if GEMINI_API_KEY else '✗ Not set'}")
print(f"   GEMINI_API_KEY value (first 20 chars): {GEMINI_API_KEY[:20] if GEMINI_API_KEY else 'None'}...")
print(f"   GEMINI_MODEL: {GEMINI_MODEL}")
print(f"   GEMINI_BASE_URL: {GEMINI_BASE_URL or 'None'}")
print(f"   GEMINI_ENABLED: {GEMINI_ENABLED}")

# Test 3: Try to import genai
print(f"\n3. Testing genai import:")
try:
    from google import genai
    from google.genai import types as genai_types
    print(f"   ✓ Successfully imported google.genai")
except Exception as e:
    print(f"   ✗ Failed to import: {e}")
    pytest.skip("google.genai SDK is not available in this environment", allow_module_level=True)

# Test 4: Try to create client
print(f"\n4. Testing Gemini client creation:")
try:
    if GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print(f"   ✓ Client created successfully")
        
        # Test 5: Try a simple generate_content call
        print(f"\n5. Testing generate_content:")
        try:
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=[genai_types.Content(role='user', parts=[genai_types.Part(text='Hello')])],
                config=genai_types.GenerateContentConfig(max_output_tokens=100),
            )
            print(f"   ✓ API call successful")
            print(f"   Response: {response.text[:100]}...")
        except Exception as e:
            print(f"   ✗ API call failed: {e}")
    else:
        print(f"   ✗ GEMINI_API_KEY not set")
except Exception as e:
    print(f"   ✗ Client creation failed: {e}")
    import traceback
    traceback.print_exc()
