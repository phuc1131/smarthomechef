#!/usr/bin/env python
"""Test script cho recipe generator API endpoints."""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

test_cases = [
    {
        "endpoint": "/api/ai/recommend-recipes/",
        "payload": {
            "ingredients": ["trứng", "thịt heo", "hành", "cơm"]
        },
        "description": "Recommend recipes from ingredients",
    },
    {
        "endpoint": "/api/ai/recommend-recipes/",
        "payload": {
            "ingredients": ["cá hồi", "cà chua", "hành lá", "dầu ăn"]
        },
        "description": "Recommend recipes (seafood)",
    },
    {
        "endpoint": "/api/ai/generate-recipe/",
        "payload": {
            "recipe_name": "Cơm trứng thịt heo",
            "ingredients": ["trứng", "thịt heo", "hành", "cơm", "dầu ăn", "nước mắm"]
        },
        "description": "Generate recipe details",
    },
]

print("=" * 80)
print("TEST: Recipe Generator API Endpoints")
print("=" * 80)

for i, test_case in enumerate(test_cases, 1):
    print(f"\n[Test {i}] {test_case['description']}")
    print(f"Endpoint: {test_case['endpoint']}")
    print("-" * 80)
    
    try:
        url = f"{BASE_URL}{test_case['endpoint']}"
        response = requests.post(url, json=test_case['payload'], timeout=15)
        
        print(f"Status Code: {response.status_code}")
        
        data = response.json()
        print(f"Success: {data.get('success')}")
        
        if 'recipes' in data:
            recipes = data.get('recipes', [])
            print(f"Number of recipes: {len(recipes)}")
            for j, recipe in enumerate(recipes[:3], 1):  # Show first 3
                print(f"  {j}. {recipe.get('name')} - {recipe.get('difficulty')}")
        
        if 'recipe' in data and data.get('recipe'):
            recipe = data.get('recipe')
            print(f"Recipe: {recipe.get('name')}")
            print(f"  Time: {recipe.get('time_minutes')} minutes")
            print(f"  Servings: {recipe.get('servings')}")
        
        print(f"Message: {data.get('message')}")
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to server. Make sure Django server is running on port 8000.")
    except Exception as e:
        print(f"ERROR: {str(e)}")

print("\n" + "=" * 80)
print("TEST COMPLETED")
print("=" * 80)
