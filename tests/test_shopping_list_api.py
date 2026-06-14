import json
from decimal import Decimal
from datetime import date

import pytest
from django.test import TestCase

from apps.users.models import Account
from apps.nutrition.models import Food, FoodCategory, Ingredient, FoodIngredient
from apps.meal_plans.models import MealPlan


class ShoppingListApiTest(TestCase):
    def setUp(self):
        self.account = Account.objects.create(
            username='api_user',
            email='api_user@example.com',
            password_hash='hash',
            role='user',
            is_active=True,
        )

        self.category = FoodCategory.objects.create(name='Món canh')

        self.food = Food.objects.create(
            name='Canh cua',
            category=self.category,
            calories=120,
            protein=8,
            carbs=10,
            fat=5,
            fiber=1,
        )

        self.egg = Ingredient.objects.create(name='Trứng')
        self.crab = Ingredient.objects.create(name='Cua')

        FoodIngredient.objects.create(food=self.food, ingredient=self.egg, quantity=2.0)
        FoodIngredient.objects.create(food=self.food, ingredient=self.crab, quantity=150.0)

        self.meal_plan = MealPlan.objects.create(
            account=self.account,
            food=self.food,
            date=date.today().isoformat(),
            meal_type='Bữa tối',
            servings=Decimal('1.5'),
        )

    @pytest.mark.xfail(reason="Shopping list API endpoint not yet implemented")
    def test_shopping_list_endpoint_returns_shopping_items(self):
        client = self.client
        session = client.session
        session['user_id'] = self.account.id
        session['user_name'] = self.account.username
        session['user_email'] = self.account.email
        session.save()

        payload = {
            'date_start': self.meal_plan.date,
            'date_end': self.meal_plan.date,
        }
        response = client.post(
            '/api/ai/generate-shopping-list/',
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('meal_plan_count'), 1)
        self.assertIn('shopping_items', data)
        self.assertGreaterEqual(len(data['shopping_items']), 1)
        self.assertIn('estimated_cost', data)
        self.assertIn('optimization', data)

        names = [item['ingredient_name'] for item in data['shopping_items']]
        self.assertIn('Trứng', names)
        self.assertIn('Cua', names)
