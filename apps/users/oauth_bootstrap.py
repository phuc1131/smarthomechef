"""Bootstrap Google OAuth configuration from environment variables."""

from __future__ import annotations

import os

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp


def _preferred_site_domain():
    explicit_domain = os.environ.get('GOOGLE_SITE_DOMAIN', '').strip()
    if explicit_domain:
        return explicit_domain

    allowed_hosts = [
        host.strip()
        for host in os.environ.get('ALLOWED_HOSTS', '').split(',')
        if host.strip() and host.strip() != '*'
    ]

    for host in allowed_hosts:
        if host not in {'localhost', '127.0.0.1'}:
            return host

    if 'localhost' in allowed_hosts:
        return 'localhost'
    if '127.0.0.1' in allowed_hosts:
        return '127.0.0.1'

    return 'localhost'


def ensure_google_social_app():
    """Create or update the Google SocialApp and link it to the active site."""
    client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()

    if not client_id or not client_secret:
        return None

    site_domain = _preferred_site_domain()
    site_name = os.environ.get('GOOGLE_SITE_NAME', '').strip() or 'Smart Home Chef'

    site, _ = Site.objects.update_or_create(
        id=int(os.environ.get('SITE_ID', '1')),
        defaults={'domain': site_domain, 'name': site_name},
    )

    social_app, _ = SocialApp.objects.update_or_create(
        provider='google',
        defaults={
            'name': 'Google',
            'client_id': client_id,
            'secret': client_secret,
        },
    )

    social_app.sites.set([site])
    return social_app
