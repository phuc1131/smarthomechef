#!/usr/bin/env python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')

import django
django.setup()

from django.db import connection
from django.db.utils import OperationalError

print("=" * 70)
print("VERIFYING TABLES IN POSTGRESQL DATABASE")
print("=" * 70)

try:
    with connection.cursor() as cursor:
        # Get all tables
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        print(f"\nTotal tables: {len(tables)}\n")
        for table in tables:
            table_name = table[0]
            
            # Check row count
            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                count = cursor.fetchone()[0]
                print(f"  {table_name:40} ({count} rows)")
            except Exception as e:
                print(f"  {table_name:40} (ERROR: {e})")
        
        # Specifically check for meal_plans
        print("\n" + "=" * 70)
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'meal_plans'
            )
        """)
        exists = cursor.fetchone()[0]
        print(f"meal_plans table exists: {exists}")
        
        if not exists:
            print("\nSearching for similar table names:")
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name LIKE '%meal%'
            """)
            similar = cursor.fetchall()
            for t in similar:
                print(f"  - {t[0]}")
        
except OperationalError as e:
    print(f"Database connection error: {e}")
    print("\nMake sure PostgreSQL is running and DATABASE_URL is set correctly.")
