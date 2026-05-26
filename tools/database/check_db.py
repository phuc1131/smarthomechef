#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from django.conf import settings

db_config = settings.DATABASES.get('default', {})
engine = db_config.get('ENGINE', 'unknown')
name = db_config.get('NAME', 'unknown')

print('=' * 60)
print('CURRENT DATABASE CONFIGURATION')
print('=' * 60)
print(f'\nEngine: {engine}')
print(f'Database Name/File: {name}')

if 'sqlite' in engine.lower():
    db_path = os.path.abspath(name) if not os.path.isabs(name) else name
    if os.path.exists(db_path):
        size_mb = os.path.getsize(db_path) / (1024*1024)
        print(f'File Path: {db_path}')
        print(f'File Size: {size_mb:.2f} MB')
        print(f'File Exists:  YES')
    else:
        print(f'File Path: {db_path}')
        print(f'File Exists:  NO (Not created yet)')

elif 'postgre' in engine.lower():
    print(f'Host: {db_config.get("HOST", "localhost")}')
    print(f'Port: {db_config.get("PORT", 5432)}')
    print(f'User: {db_config.get("USER", "unknown")}')
    print(f'Database Name: {name}')

print('\nFull Config:')
for key, value in db_config.items():
    if key != 'PASSWORD':
        print(f'  {key}: {value}')
    else:
        print(f'  {key}: {"*" * 8}')

print('\n' + '=' * 60)
print('DATABASE TABLES & RECORDS')
print('=' * 60)

# Check Account records
from apps.users.models import Account
print(f'\nAccount table: {Account._meta.db_table}')
print(f'  Total accounts: {Account.objects.count()}')
print(f'  Active accounts: {Account.objects.filter(is_active=True).count()}')
print(f'  Admin accounts: {Account.objects.filter(role="admin").count()}')

# List accounts
print('\n  Sample accounts:')
for acc in Account.objects.all()[:5]:
    print(f'    - {acc.username} ({acc.role}) - {acc.email}')

print('=' * 60)
