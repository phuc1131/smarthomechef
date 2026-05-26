#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print('\n=== TẤT CẢ CÁC BẢNG TRONG DATABASE ===')
for table in tables:
    print(f'  [OK] {table[0]}')
print(f'\nTổng cộng: {len(tables)} bảng')

# Check APP models
print('\n=== BẢNG CỦA APP ===')
app_tables = [t for t in tables if not t[0].startswith('auth_') and not t[0].startswith('django_')]
for table in app_tables:
    print(f'  [OK] {table[0]}')
print(f'Tổng: {len(app_tables)} bảng app')
