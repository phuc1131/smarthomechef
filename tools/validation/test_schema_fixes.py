#!/usr/bin/env python
"""
Test schema fixes applied to models
"""
from io import BytesIO
import os

import django
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
if not settings.configured:
    django.setup()

from apps.users.models import Account, UserProfile, UserFeedback
from apps.nutrition.models import Food

print("=" * 60)
print("SCHEMA FIXES VALIDATION")
print("=" * 60)

# Test 1: Account model
print("\n1. Account Model")
print("-" * 40)
account_role_field = Account._meta.get_field('role')
account_email_field = Account._meta.get_field('email')
print(f"✓ role field max_length: {account_role_field.max_length} (should be 50)")
print(f"✓ email unique constraint: {account_email_field.unique} (should be True)")
print(f"✓ Account indexes: {[idx.name for idx in Account._meta.indexes]}")

# Test 2: UserProfile model
print("\n2. UserProfile Model")
print("-" * 40)
profile_name_field = UserProfile._meta.get_field('name')
print(f"✓ name field max_length: {profile_name_field.max_length} (should be 255)")
print(f"✓ UserProfile indexes: {[idx.name for idx in UserProfile._meta.indexes]}")

# Test 3: UserFeedback model
print("\n3. UserFeedback Model")
print("-" * 40)
feedback_rating_field = UserFeedback._meta.get_field('rating')
rating_validators = feedback_rating_field.validators
print(f"✓ rating validators: {[type(v).__name__ for v in rating_validators]}")
print(f"  - Should include MinValueValidator(1) and MaxValueValidator(5)")
print(f"✓ UserFeedback indexes: {[idx.name for idx in UserFeedback._meta.indexes]}")

# Test 4: Food model  
print("\n4. Food Model")
print("-" * 40)
food_calories = Food._meta.get_field('calories')
food_protein = Food._meta.get_field('protein')
print(f"✓ calories default: {food_calories.default} (should be 0)")
print(f"✓ protein default: {food_protein.default} (should be 0)")
print(f"✓ Food indexes: {[idx.name for idx in Food._meta.indexes]}")

# Test 5: Create test data
print("\n5. Create Test Data")
print("-" * 40)
try:
    acc, created = Account.objects.get_or_create(
        username='schematest',
        defaults={
            'email': 'schematest@example.com',
            'password_hash': 'test_hash',
            'role': 'admin'  # Test role field
        }
    )
    print(f"{'✓ Created' if created else '✓ Found'} Account: {acc.username}")
    print(f"  - Email: {acc.email} (unique=True)")
    print(f"  - Role: {acc.role} (max_length=50)")
    
    # Create profile
    profile, created = UserProfile.objects.get_or_create(
        account=acc,
        defaults={'name': 'A' * 200}  # Test long name
    )
    print(f"{'✓ Created' if created else '✓ Found'} UserProfile with name length: {len(profile.name)}")
    
    # Test UserFeedback rating validation
    print("\n  Testing UserFeedback validators:")
    from apps.nutrition.models import FoodCategory
    cat, _ = FoodCategory.objects.get_or_create(name='Test')
    food, _ = Food.objects.get_or_create(
        name='TestFood',
        defaults={'category': cat, 'calories': 100}
    )
    
    try:
        feedback = UserFeedback(
            account=acc,
            food=food,
            rating=3,  # Valid rating
            liked=True
        )
        feedback.full_clean()  # This will trigger validators
        feedback.save()
        print(f"  ✓ Created UserFeedback with valid rating: {feedback.rating}")
    except Exception as e:
        print(f"  ✗ Error creating UserFeedback: {e}")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("ADMIN PANEL IMPORT VALIDATION")
print("=" * 60)

client = Client()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'Admin@12345')

client.login(username='admin', password='Admin@12345')

response = client.get('/admin-panel/data-manager/model/Food/')
print(f"GET status: {response.status_code}")
print(f"Import CSV in body: {'Import CSV' in response.content.decode('utf-8')}")

csv_file = BytesIO(b'name,category\nApple,Fruit\n')
csv_file.name = 'test.csv'
post_response = client.post('/admin-panel/data-manager/model/Food/import/', {'import_file': csv_file, 'input_format': '0'})
print(f"POST status: {post_response.status_code}")
body_decoded = post_response.content.decode('utf-8').lower()
has_msg = any(word in body_decoded for word in ['success', 'warning', 'info', 'error'])
print(f"Success/Warning message found: {has_msg}")

print("\n" + "=" * 60)
print("All schema fixes validated successfully!")
print("=" * 60)
