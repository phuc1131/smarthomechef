#!/usr/bin/env python
import os
import django
from django.utils import timezone
from django.contrib.auth.hashers import make_password

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from django.db import connection
from django.contrib.auth.models import User

# Delete existing admin user if exists
User.objects.filter(username='admin').delete()
print("Cleaned up existing admin user")

# Use raw SQL to create user with last_login set to now
cursor = connection.cursor()
now = timezone.now()
password_hash = make_password('Admin@123456')

cursor.execute(
    """
    INSERT INTO auth_user 
    (password, last_login, is_superuser, is_staff, username, first_name, last_name, email, is_active, date_joined)
    VALUES (%s, %s, true, true, %s, '', '', %s, true, %s)
    """,
    [password_hash, now, 'admin', 'admin@smartchef.local', now]
)

print(f"✅ Superuser 'admin' created successfully!")
print(f"   Username: admin")
print(f"   Email: admin@smartchef.local")
print(f"   Password: Admin@123456")
