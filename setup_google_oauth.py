#!/usr/bin/env python
"""Setup Google OAuth SocialApp in AllAuth."""

import argparse
import os
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from apps.users.oauth_bootstrap import ensure_google_social_app


def main():
    parser = argparse.ArgumentParser(
        description='Bootstrap Google OAuth SocialApp for django-allauth.'
    )
    parser.add_argument('--client-id', dest='client_id', default=None)
    parser.add_argument('--client-secret', dest='client_secret', default=None)
    parser.add_argument('--site-domain', dest='site_domain', default=None)
    parser.add_argument('--site-name', dest='site_name', default=None)
    args = parser.parse_args()

    client_id = args.client_id or os.environ.get('GOOGLE_CLIENT_ID', '').strip()
    client_secret = args.client_secret or os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()

    if args.site_domain:
        os.environ['GOOGLE_SITE_DOMAIN'] = args.site_domain
    if args.site_name:
        os.environ['GOOGLE_SITE_NAME'] = args.site_name

    if not client_id or not client_secret:
        print('ERROR: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not provided.')
        print('Provide them via:')
        print('  1. .env file (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET), or')
        print('  2. --client-id and --client-secret arguments, or')
        print('  3. Environment variables')
        raise SystemExit(1)

    app = ensure_google_social_app()

    if app is None:
        print('ERROR: Failed to create SocialApp.')
        raise SystemExit(1)

    print('✓ Google OAuth is now configured!')
    print(f'  Provider: {app.provider}')
    print(f'  Name: {app.name}')
    print(f'  Client ID: {app.client_id[:30]}...')
    print(f"  Sites: {', '.join([s.domain for s in app.sites.all()])}")


if __name__ == '__main__':
    main()
