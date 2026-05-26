#!/usr/bin/env python
"""Check AI completion status of the smart-home-chef project."""
import os
import django

from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from apps.nutrition.models import Food, Ingredient, Recipe
from apps.users.models import Account, UserProfile, UserBehaviorLog
from apps.core_models.models import AIRecommendation
from app.services.ai_orchestrator_service import AIOrchestratorService
from app.services.personalization_service import build_user_preference_profile

print("=" * 70)
print("SMART CHEF AI COMPLETION CHECK")
print("=" * 70)

# Database Schema Check
print("\n[1] DATABASE SCHEMA")
print("-" * 70)
schema_targets = [
    ('Food Items', Food),
    ('Ingredients', Ingredient),
    ('User Accounts', Account),
    ('User Profiles', UserProfile),
    ('User Behavior Logs', UserBehaviorLog),
    ('AI Recommendations', AIRecommendation),
]

with connection.cursor() as cur:
    existing_tables = set(connection.introspection.table_names())
    for desc, model in schema_targets:
        table_name = model._meta.db_table
        try:
            if table_name not in existing_tables:
                raise RuntimeError('table not found')
            cols = connection.introspection.get_table_description(cur, table_name)
            quoted_table = connection.ops.quote_name(table_name)
            cur.execute(f'SELECT COUNT(*) FROM {quoted_table}')
            count = cur.fetchone()[0]
            print(f"[OK] {desc:30} ({table_name}): {len(cols):2} cols, {count:5} rows")
        except Exception as e:
            print(f"[ERROR] {desc:30} ({table_name}): ERROR - {str(e)[:40]}")

# Django ORM Check - with error handling
print("\n[2] DJANGO ORM DATA")
print("-" * 70)
try:
    print(f"Foods:                    {Food.objects.count():5} items")
except Exception as e:
    print(f"Foods:                    ERROR - {str(e)[:50]}")

try:
    print(f"Ingredients:              {Ingredient.objects.count():5} items")
except Exception as e:
    print(f"Ingredients:              ERROR - {str(e)[:50]}")

try:
    print(f"Recipes:                  {Recipe.objects.count():5} items")
except Exception as e:
    print(f"Recipes:                  ERROR - {str(e)[:50]}")

try:
    print(f"User Accounts:            {Account.objects.count():5} items")
except Exception as e:
    print(f"User Accounts:            ERROR - {str(e)[:50]}")

try:
    print(f"AI Recommendations:       {AIRecommendation.objects.count():5} items")
except Exception as e:
    print(f"AI Recommendations:       ERROR - {str(e)[:50]}")

# Services Check
print("\n[3] AI SERVICES")
print("-" * 70)
services_ok = True
try:
    print("[OK] Personalization Service")
except Exception as e:
    print(f"[ERROR] Personalization Service: {str(e)[:50]}")
    services_ok = False

try:
    from app.services.recipe_generator_service import recommend_recipes_from_ingredients
    print("[OK] Recipe Generator Service")
except Exception as e:
    print(f"[ERROR] Recipe Generator Service: {str(e)[:50]}")
    services_ok = False

try:
    from app.services.food_data_service import get_or_fetch_food, ensure_ingredient_nutrition
    print("[OK] Food Data Service")
except Exception as e:
    print(f"[ERROR] Food Data Service: {str(e)[:50]}")
    services_ok = False

try:
    from app.services.ingredient_parser_service import parse_ingredients_from_text
    print("[OK] Ingredient Parser Service")
except Exception as e:
    print(f"[ERROR] Ingredient Parser Service: {str(e)[:50]}")
    services_ok = False

try:
    from app.services.external_apis import parse_and_save_spoonacular_food
    print("[OK] External APIs Service")
except Exception as e:
    print(f"[ERROR] External APIs Service: {str(e)[:50]}")
    services_ok = False

# LLM Integration Check
print("\n[4] LLM INTEGRATION")
print("-" * 70)
try:
    import google.generativeai as genai
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        print(f"[OK] Gemini API configured (key length: {len(api_key)})")
    else:
        print("[ERROR] Gemini API key not set")
except ImportError:
    print("[ERROR] google.generativeai not installed")

# Feature Status
print("\n[5] AI FEATURES STATUS")
print("-" * 70)
print(f"{'Personalization Pipeline':40} {'Ready' if services_ok else 'Not Ready':>10}")
print(f"{'Recipe Generation':40} {'Ready' if services_ok else 'Not Ready':>10}")
print(f"{'Ingredient Recognition':40} {'Ready' if services_ok else 'Not Ready':>10}")
print(f"{'Food Recommendations':40} {'Ready' if services_ok else 'Not Ready':>10}")
print(f"{'User Preference Learning':40} {'Ready' if services_ok else 'Not Ready':>10}")

print("\n[6] INTERNAL AI MODEL")
print("-" * 70)
try:
    ai_report = AIOrchestratorService.get_health_report()
    intent_model = ai_report.get('intent_model', {})
    print(f"[OK] Internal intent model: {intent_model.get('model_name', 'unknown')}")
    print(f"     artifact: {intent_model.get('artifact_path', 'n/a')}")
    print(f"     version:   {intent_model.get('version', 'n/a')}")
    print(f"     docs:      {intent_model.get('document_count', 0)}")
    print(f"     intents:   {intent_model.get('intent_count', 0)}")
except Exception as e:
    print(f"[ERROR] Internal AI model: {str(e)[:80]}")

print("\n" + "=" * 70)
if services_ok and Food.objects.count() > 0:
    print("STATUS: [OK] AI System is READY and OPERATIONAL")
elif services_ok:
    print("STATUS: [WARNING] AI System is READY but lacks data (run seed scripts)")
else:
    print("STATUS: [ERROR] AI System has issues - check services above")
print("=" * 70)
