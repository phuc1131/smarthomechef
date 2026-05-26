#!/usr/bin/env python
"""Create missing database tables for users and AI recommendations."""
import os
import django
import sqlite3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

print("Creating missing database tables...")

# Create users app tables
print("- Creating apps_users_account...")
cur.execute('''
CREATE TABLE IF NOT EXISTS apps_users_account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(254),
    role VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

print("- Creating apps_users_userbehaviorprofile...")
cur.execute('''
CREATE TABLE IF NOT EXISTS apps_users_userbehaviorprofile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    preferred_macros TEXT,
    disliked_ingredients TEXT,
    eating_patterns TEXT,
    created_at DATETIME,
    FOREIGN KEY (account_id) REFERENCES apps_users_account(id)
)
''')

print("- Creating apps_users_disease...")
cur.execute('''
CREATE TABLE IF NOT EXISTS apps_users_disease (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(150) UNIQUE,
    description TEXT
)
''')

print("- Creating apps_users_goal...")
cur.execute('''
CREATE TABLE IF NOT EXISTS apps_users_goal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(150) UNIQUE,
    description TEXT
)
''')

print("- Creating apps_users_userbudgetlog...")
cur.execute('''
CREATE TABLE IF NOT EXISTS apps_users_userbudgetlog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    amount DECIMAL(10,2),
    created_at DATETIME,
    FOREIGN KEY (account_id) REFERENCES apps_users_account(id)
)
''')

print("- Creating apps_users_userfeedback...")
cur.execute('''
CREATE TABLE IF NOT EXISTS apps_users_userfeedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    food_id INTEGER,
    rating INTEGER,
    created_at DATETIME,
    FOREIGN KEY (account_id) REFERENCES apps_users_account(id),
    FOREIGN KEY (food_id) REFERENCES foods(id)
)
''')

# Create core_models tables
print("- Creating apps_core_models_airecommendation...")
cur.execute('''
CREATE TABLE IF NOT EXISTS apps_core_models_airecommendation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    food_id INTEGER,
    score DECIMAL(5,2),
    budget_score DECIMAL(5,2),
    estimated_cost DECIMAL(10,2),
    created_at DATETIME,
    FOREIGN KEY (account_id) REFERENCES apps_users_account(id),
    FOREIGN KEY (food_id) REFERENCES foods(id)
)
''')

print("- Creating apps_core_models_searchevent...")
cur.execute('''
CREATE TABLE IF NOT EXISTS apps_core_models_searchevent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER,
    query VARCHAR(255),
    clicked_food_id INTEGER,
    created_at DATETIME,
    FOREIGN KEY (account_id) REFERENCES apps_users_account(id),
    FOREIGN KEY (clicked_food_id) REFERENCES foods(id)
)
''')

conn.commit()
conn.close()
print("\n[OK] All missing tables created successfully!")
