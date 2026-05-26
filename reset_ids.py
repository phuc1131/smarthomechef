#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

# Delete all data
cursor.execute('DELETE FROM foods')
cursor.execute('DELETE FROM food_categories')

# Reset sequence for FoodCategory
try:
    cursor.execute("SELECT setval(pg_get_serial_sequence('nutrition_foodcategory', 'id'), 1, false)")
    print("✓ Reset sequence for food_categories")
except Exception as e:
    print(f"Note: {e}")

connection.commit()
print("✓ All data deleted and sequences reset")
