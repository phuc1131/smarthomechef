#!/usr/bin/env python
"""
Clean PostgreSQL setup - drop and recreate database
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Read from .env
def load_env():
    env_vars = {}
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars

env_vars = load_env()
db_name = env_vars.get('DB_NAME', 'smart_home_chef')
db_user = env_vars.get('DB_USER', 'postgres')
db_password = env_vars.get('DB_PASSWORD', '123456')
db_host = env_vars.get('DB_HOST', 'localhost')
db_port = int(env_vars.get('DB_PORT', 5432))

print("=" * 70)
print("CLEAN POSTGRESQL DATABASE SETUP")
print("=" * 70)

try:
    # Connect to default postgres database
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database='postgres'
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Terminate existing connections
    print(f"\n[1] Terminating existing connections to '{db_name}'...")
    cursor.execute(f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{db_name}'
        AND pid <> pg_backend_pid();
    """)
    print("✓ Done")
    
    # Drop database if exists
    print(f"[2] Dropping database '{db_name}' if exists...")
    cursor.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
    print("✓ Done")
    
    # Create fresh database
    print(f"[3] Creating fresh database '{db_name}'...")
    cursor.execute(f'CREATE DATABASE "{db_name}"')
    print("✓ Done")
    
    cursor.close()
    conn.close()
    
    print("\n✅ Clean database created successfully!")
    print(f"\nDatabase: {db_name}")
    print(f"Host: {db_host}:{db_port}")
    print(f"User: {db_user}")
    print("\n" + "=" * 70)
    
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
