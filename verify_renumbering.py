#!/usr/bin/env python
"""Verify that all table IDs are now sequential."""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

# Tables to verify
tables = [
    'foods',
    'food_categories',
    'food_ingredients',
    'food_recipes',
    'food_popularity',
    'meal_plans',
    'chat_sessions',
    'chat_messages',
    'intents',
    'accounts',
]

print("\n=== Verifying Renumbering Results ===\n")

for table in tables:
    # Check if table exists
    cursor.execute("""
        SELECT EXISTS(
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = %s
        )
    """, [table])
    
    if not cursor.fetchone()[0]:
        print(f"  {table}: DOES NOT EXIST")
        continue
    
    # Get count and ID range
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print(f"  {table}: empty")
        continue
    
    cursor.execute(f"SELECT MIN(id), MAX(id) FROM {table}")
    min_id, max_id = cursor.fetchone()
    
    # Check for gaps
    cursor.execute(f"SELECT id FROM {table} ORDER BY id")
    ids = [row[0] for row in cursor.fetchall()]
    
    expected_ids = list(range(1, count + 1))
    gaps = set(expected_ids) - set(ids)
    
    if gaps:
        print(f"  {table}: {count} rows, IDs 1-{count} but MISSING: {sorted(gaps)}")
    elif ids == expected_ids:
        print(f"  {table}: ✓ {count} rows, IDs 1-{count} (sequential)")
    else:
        print(f"  {table}: {count} rows, IDs {min_id}-{max_id} - ISSUE")

print("\n=== Verification complete ===\n")
