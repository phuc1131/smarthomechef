#!/usr/bin/env python
"""
Setup PostgreSQL database and migrate data from SQLite
"""
import os
import sys
import django
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from django.conf import settings
from django.db import connection

# Get PostgreSQL config
db_config = settings.DATABASES['default']
db_name = db_config['NAME']
db_user = db_config['USER']
db_password = db_config['PASSWORD']
db_host = db_config['HOST']
db_port = db_config['PORT']

print("=" * 70)
print("POSTGRESQL DATABASE SETUP & MIGRATION")
print("=" * 70)

# Step 1: Create database if not exists
print("\n[Step 1] Creating PostgreSQL database...")
try:
    # Connect to default postgres database to create new database
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database='postgres'
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Check if database exists
    cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
    if cursor.fetchone():
        print(f"✓ Database '{db_name}' already exists")
    else:
        cursor.execute(f'CREATE DATABASE "{db_name}"')
        print(f"✓ Created database '{db_name}'")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"✗ Error creating database: {e}")
    sys.exit(1)

# Step 2: Test connection to new database
print("\n[Step 2] Testing connection to new database...")
try:
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name
    )
    conn.close()
    print(f"✓ Successfully connected to '{db_name}'")
except Exception as e:
    print(f"✗ Connection failed: {e}")
    sys.exit(1)

# Step 3: Run Django migrations
print("\n[Step 3] Running Django migrations on PostgreSQL...")
try:
    from django.core.management import call_command
    call_command('migrate', verbosity=2)
    print("✓ All migrations applied successfully")
except Exception as e:
    print(f"✗ Migration failed: {e}")
    sys.exit(1)

# Step 4: Migrate data from SQLite to PostgreSQL
print("\n[Step 4] Migrating data from SQLite to PostgreSQL...")
try:
    from apps.users.models import Account, UserProfile, UserGoal, UserFeedback
    from apps.nutrition.models import Food, FoodCategory, Recipe
    
    # Open SQLite connection for reading
    import sqlite3
    sqlite_db = os.path.join(os.path.dirname(__file__), 'smart-home-chef')
    
    if not os.path.exists(sqlite_db):
        print(f"ℹ SQLite database not found at {sqlite_db}")
        print("  Skipping data migration (fresh PostgreSQL setup)")
    else:
        sqlite_conn = sqlite3.connect(sqlite_db)
        sqlite_conn.row_factory = sqlite3.Row
        
        # Migrate Account
        cursor = sqlite_conn.cursor()
        cursor.execute('SELECT * FROM users')
        accounts = cursor.fetchall()
        
        if accounts:
            print(f"\n  Migrating {len(accounts)} accounts...")
            for row in accounts:
                acc, created = Account.objects.get_or_create(
                    id=row['id'],
                    defaults={
                        'username': row['username'],
                        'email': row['email'],
                        'password_hash': row['password_hash'],
                        'role': row['role'],
                        'is_active': row['is_active'],
                        'created_at': row['created_at'],
                    }
                )
                if created:
                    print(f"    ✓ {row['username']}")
        
        # Migrate FoodCategory
        cursor.execute('SELECT * FROM food_categories')
        categories = cursor.fetchall()
        
        if categories:
            print(f"\n  Migrating {len(categories)} food categories...")
            for row in categories:
                cat, created = FoodCategory.objects.get_or_create(
                    id=row['id'],
                    defaults={'name': row['name']}
                )
        
        # Migrate Food
        cursor.execute('SELECT * FROM foods LIMIT 20')
        foods = cursor.fetchall()
        
        if foods:
            print(f"\n  Migrating {len(foods)} foods (first 20)...")
            for row in foods:
                food, created = Food.objects.get_or_create(
                    id=row['id'],
                    defaults={
                        'name': row['name'],
                        'normalized_name': row.get('normalized_name'),
                        'category_id': row.get('category_id'),
                        'calories': row.get('calories', 0),
                        'protein': row.get('protein', 0),
                        'carbs': row.get('carbs', 0),
                        'fat': row.get('fat', 0),
                        'fiber': row.get('fiber', 0),
                        'is_vegetarian': row.get('is_vegetarian', False),
                        'is_diabetes_friendly': row.get('is_diabetes_friendly', False),
                        'is_weight_loss_friendly': row.get('is_weight_loss_friendly', False),
                    }
                )
        
        sqlite_conn.close()
        print("\n✓ Data migration completed")

except Exception as e:
    print(f"✗ Data migration error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("✅ PostgreSQL Setup Complete!")
print("=" * 70)
print(f"\nDatabase: {db_name}")
print(f"Host: {db_host}:{db_port}")
print(f"User: {db_user}")
print("\nYou can now run the Django server:")
print("  python manage.py runserver 127.0.0.1:8000")
print("=" * 70)
