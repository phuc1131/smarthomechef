import os
import pytest
import django
from django.contrib.auth.hashers import make_password
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from apps.users.models import Account
from django.test import RequestFactory
from apps.users.views import accounts_list, account_detail

pytestmark = pytest.mark.django_db


def test_accounts_api_functions_smoke():
    print('=== TEST ACCOUNTS API FUNCTIONS ===')

    admin_account = Account.objects.create(
        username='admin_functions_test',
        email='admin_functions_test@example.com',
        password_hash=make_password('admin123'),
        role='admin',
        is_active=True,
    )
    target_account = Account.objects.create(
        username='user_functions_test',
        email='user_functions_test@example.com',
        password_hash=make_password('user123'),
        role='user',
        is_active=True,
    )

    factory = RequestFactory()

    request = factory.get('/api/accounts/list/')
    request.session = {'user_id': admin_account.id}
    response = accounts_list(request)
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data.get('total', 0) >= 2

    request2 = factory.get(f'/api/accounts/{target_account.id}/')
    request2.session = {'user_id': admin_account.id}
    response2 = account_detail(request2, target_account.id)
    assert response2.status_code == 200
    detail_data = json.loads(response2.content)
    assert detail_data.get('account', {}).get('username') == target_account.username

    request3 = factory.get('/api/accounts/list/')
    request3.session = {'user_id': target_account.id}
    response3 = accounts_list(request3)
    assert response3.status_code == 403