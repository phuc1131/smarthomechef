#!/usr/bin/env python
"""Recreate tables with correct names matching model db_table definitions."""
import os
import django
import sqlite3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

print("Dropping app-prefixed tables...")
for table in ['apps_users_account', 'apps_users_userbehaviorprofile', 'apps_users_disease', 
              'apps_users_goal', 'apps_users_userbudgetlog', 'apps_users_userfeedback',
              'apps_core_models_airecommendation', 'apps_core_models_searchevent']:
    try:
        cur.execute(f'DROP TABLE IF EXISTS {table}')
        print(f"  - Dropped {table}")
    except:
        pass

conn.commit()

print("\nCreating tables with correct names...")

# Create users tables with correct db_table names
print("- Creating users (Account)...")
cur.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(254),
    role VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

print("- Creating user_behavior_profiles...")
cur.execute('''
CREATE TABLE IF NOT EXISTS user_behavior_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER UNIQUE,
    preferred_macros TEXT,
    disliked_ingredients TEXT,
    eating_patterns TEXT,
    created_at DATETIME,
    FOREIGN KEY (account_id) REFERENCES users(id) ON DELETE CASCADE
)
''')

print("- Creating user_profiles...")
cur.execute('''
CREATE TABLE IF NOT EXISTS user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER UNIQUE,
    bio TEXT,
    created_at DATETIME,
    FOREIGN KEY (account_id) REFERENCES users(id) ON DELETE CASCADE
)
''')

print("- Creating diseases...")
cur.execute('''
CREATE TABLE IF NOT EXISTS diseases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(150) UNIQUE,
    description TEXT
)
''')

print("- Creating user_goals (legacy)...")
cur.execute('''
CREATE TABLE IF NOT EXISTS user_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    goal TEXT,
    FOREIGN KEY (account_id) REFERENCES users(id) ON DELETE CASCADE
)
''')

print("- Creating user_diseases...")
cur.execute('''
CREATE TABLE IF NOT EXISTS user_diseases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    disease_id INTEGER,
    FOREIGN KEY (account_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (disease_id) REFERENCES diseases(id)
)
''')

print("- Creating disease_nutrition_rules...")
cur.execute('''
CREATE TABLE IF NOT EXISTS disease_nutrition_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disease_id INTEGER,
    rule_type VARCHAR(50),
    value DECIMAL(10,2),
    FOREIGN KEY (disease_id) REFERENCES diseases(id)
)
''')

print("- Creating goals...")
cur.execute('''
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(150) UNIQUE,
    description TEXT
)
''')

print("- Creating goal_nutrition_rules...")
cur.execute('''
CREATE TABLE IF NOT EXISTS goal_nutrition_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id INTEGER,
    rule_type VARCHAR(50),
    value DECIMAL(10,2),
    FOREIGN KEY (goal_id) REFERENCES goals(id)
)
''')

print("- Creating user_budget_logs...")
cur.execute('''
CREATE TABLE IF NOT EXISTS user_budget_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    amount DECIMAL(10,2),
    created_at DATETIME,
    FOREIGN KEY (account_id) REFERENCES users(id) ON DELETE CASCADE
)
''')

print("- Creating user_feedback...")
cur.execute('''
CREATE TABLE IF NOT EXISTS user_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    food_id INTEGER,
    rating INTEGER,
    created_at DATETIME,
    FOREIGN KEY (account_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (food_id) REFERENCES foods(id)
)
''')

# Create core_models tables
print("- Creating ai_recommendations...")
cur.execute('''
CREATE TABLE IF NOT EXISTS ai_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    food_id INTEGER,
    score DECIMAL(5,2),
    budget_score DECIMAL(5,2),
    estimated_cost DECIMAL(10,2),
    created_at DATETIME,
    FOREIGN KEY (account_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (food_id) REFERENCES foods(id)
)
''')

print("- Creating search_events...")
cur.execute('''
CREATE TABLE IF NOT EXISTS search_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    query VARCHAR(255),
    clicked_food_id INTEGER,
    created_at DATETIME,
    FOREIGN KEY (account_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (clicked_food_id) REFERENCES foods(id)
)
''')

conn.commit()
conn.close()
print("\n[OK] All tables created with correct names!")
