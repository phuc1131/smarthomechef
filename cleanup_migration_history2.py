#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from django.db import connection

# Delete problematic migrations from history
cursor = connection.cursor()
migrations_to_delete = [
    ('chat', '0005_remove_chatresponsecache_chat_respon_account_98657b_idx_and_more'),
    ('users', '0021_remove_account_users_email_4b85f2_idx_and_more'),
    ('core_models', '0004_modelmetadata_remove_airecommendation_context_and_more'),
]

for app, migration in migrations_to_delete:
    cursor.execute(
        "DELETE FROM django_migrations WHERE app=%s AND name=%s",
        [app, migration]
    )
    print(f"Deleted {app}.{migration}")

print("Done!")
