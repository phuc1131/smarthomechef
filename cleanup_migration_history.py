#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from django.db import connection

# Delete remaining problematic migrations from history
cursor = connection.cursor()
migrations_to_delete = [
    ('app', '0004_remove_mealplan_food_remove_mealplan_account_and_more'),
]

for app, migration in migrations_to_delete:
    cursor.execute(
        "DELETE FROM django_migrations WHERE app=%s AND name=%s",
        [app, migration]
    )
    print(f"Deleted {app}.{migration}")

print("Done!")
