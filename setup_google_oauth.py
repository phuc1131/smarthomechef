#!/usr/bin/env python
"""Setup Google OAuth SocialApp in AllAuth"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

# Get Google credentials from environment
client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '')

if not client_id or not client_secret:
    print("ERROR: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set in .env")
    exit(1)

# Get or create the app
app, created = SocialApp.objects.get_or_create(
    provider='google',
    defaults={
        'name': 'Google',
        'client_id': client_id,
        'secret': client_secret,
    }
)

if created:
    print(f"✓ Created SocialApp: {app.name} (ID: {app.id})")
else:
    # Update existing app with new credentials
    app.client_id = client_id
    app.secret = client_secret
    app.save()
    print(f"✓ Updated SocialApp: {app.name} (ID: {app.id})")

# Ensure it's linked to the current site (SITE_ID = 1)
site, created = Site.objects.get_or_create(
    id=1,
    defaults={
        'domain': 'example.com',
        'name': 'Example',
    }
)

if created:
    print(f"✓ Created Site: {site.domain} (ID: {site.id})")

if site not in app.sites.all():
    app.sites.add(site)
    print(f"✓ Linked to Site: {site.domain}")
else:
    print(f"✓ Already linked to Site: {site.domain}")

print(f"\nSocialApp Details:")
print(f"  Provider: {app.provider}")
print(f"  Name: {app.name}")
print(f"  Client ID: {app.client_id[:30]}...")
print(f"  Sites: {', '.join([s.domain for s in app.sites.all()])}")
print(f"\n✓ Google OAuth is now configured!")
