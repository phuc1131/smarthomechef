#!/usr/bin/env python
"""Test script cho ingredient parser API endpoint."""
import requests
import json

URL = "http://127.0.0.1:8000/api/ai/parse-ingredients/"

test_cases = [
    "Tôi có trứng, thịt heo, hành",
    "Làm cháo từ gạo, gà và hành tây",
    "Có cá hồi, cà chua, hành lá",
]

print("=" * 70)
print("TEST: Ingredient Parser API Endpoint")
print("=" * 70)

for i, test_text in enumerate(test_cases, 1):
    print(f"\n[Test {i}]")
    print(f"Input: {test_text}")
    
    try:
        payload = {"text": test_text}
        response = requests.post(URL, json=payload, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Ingredients: {data.get('ingredients', [])}")
        print(f"Method: {data.get('method')}")
        print(f"Confidence: {data.get('confidence')}")
        print(f"Message: {data.get('message')}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

print("\n" + "=" * 70)
print("TEST COMPLETED")
print("=" * 70)
