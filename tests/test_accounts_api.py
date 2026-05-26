import os
import pytest
import django
import json

from django.contrib.auth.hashers import make_password
from django.test import Client

pytestmark = pytest.mark.django_db

os.environ['ALLOWED_HOSTS'] = 'testserver,localhost,127.0.0.1'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from apps.users.models import Account


def test_accounts_api_smoke():
    print('=== TEST ACCOUNTS API ===')

    admin_account = Account.objects.create(
        username='admin_api_test',
        email='admin_api_test@example.com',
        password_hash=make_password('admin123'),
        role='admin',
        is_active=True,
    )
    user_account = Account.objects.create(
        username='user_api_test',
        email='user_api_test@example.com',
        password_hash=make_password('user123'),
        role='user',
        is_active=True,
    )

    client = Client()
    login_data = json.dumps({'username': user_account.username, 'password': 'user123'})
    login_response = client.post('/auth/login/', login_data, content_type='application/json')
    assert login_response.status_code == 200
    assert login_response.json()['ok'] is True

    session = client.session
    session['user_id'] = admin_account.id
    session['user_name'] = admin_account.username
    session['user_email'] = admin_account.email
    session.save()

    accounts_response = client.get('/api/accounts/list/')
    assert accounts_response.status_code == 200
    data = accounts_response.json()
    assert data.get('total', 0) >= 2

    detail_response = client.get(f'/api/accounts/{user_account.id}/')
    assert detail_response.status_code == 200
    detail_data = detail_response.json()
    assert detail_data.get('account', {}).get('username') == user_account.username