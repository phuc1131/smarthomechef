#!/usr/bin/env python
"""Setup Google OAuth SocialApp in AllAuth."""

import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from apps.users.oauth_bootstrap import ensure_google_social_app


app = ensure_google_social_app()

if app is None:
    print('ERROR: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set in .env')
    raise SystemExit(1)

print('✓ Google OAuth is now configured!')
print(f'  Provider: {app.provider}')
print(f'  Name: {app.name}')
print(f'  Client ID: {app.client_id[:30]}...')
print(f"  Sites: {', '.join([s.domain for s in app.sites.all()])}")
