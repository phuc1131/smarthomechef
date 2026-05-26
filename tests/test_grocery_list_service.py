from decimal import Decimal
from datetime import date

from django.test import TestCase

from apps.users.models import Account
from apps.nutrition.models import Food, FoodCategory, FoodIngredient, Ingredient
from apps.meal_plans.models import MealPlan
from services.grocery_list_service import (
    generate_shopping_list_from_meal_plan,
    calculate_shopping_cost_estimate,
    suggest_shopping_optimization,
)


class GroceryListServiceTest(TestCase):
    def setUp(self):
        self.account = Account.objects.create(
            username='test_shopping_user',
            email='test_shopping@example.com',
            password_hash='testhash',
            role='user',
            is_active=True,
        )

        self.category = FoodCategory.objects.create(name='Thực phẩm')

        self.food = Food.objects.create(
            name='Cơm trứng',
            category=self.category,
            calories=200,
            protein=10,
            carbs=30,
            fat=8,
            fiber=2,
        )

        self.ingredient_egg = Ingredient.objects.create(name='Trứng')
        self.ingredient_rice = Ingredient.objects.create(name='Gạo')

        FoodIngredient.objects.create(food=self.food, ingredient=self.ingredient_egg, quantity=2.0)
        FoodIngredient.objects.create(food=self.food, ingredient=self.ingredient_rice, quantity=150.0)

        self.meal_plan = MealPlan.objects.create(
            account=self.account,
            food=self.food,
            date=date.today().isoformat(),
            meal_type='Bữa trưa',
            servings=Decimal('2'),
        )

    def test_generate_shopping_list_from_meal_plan(self):
        result = generate_shopping_list_from_meal_plan(
            self.account,
            date_start=self.meal_plan.date,
            date_end=self.meal_plan.date,
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['meal_plan_count'], 1)
        self.assertEqual(result['date_range']['start'], self.meal_plan.date)
        self.assertEqual(result['date_range']['end'], self.meal_plan.date)
        self.assertEqual(len(result['shopping_items']), 2)

        item_names = [item['ingredient_name'] for item in result['shopping_items']]
        self.assertIn('Trứng', item_names)
        self.assertIn('Gạo', item_names)

        egg_item = next(item for item in result['shopping_items'] if item['ingredient_name'] == 'Trứng')
        rice_item = next(item for item in result['shopping_items'] if item['ingredient_name'] == 'Gạo')

        self.assertEqual(egg_item['unit'], 'cái')
        self.assertEqual(egg_item['total_quantity'], 4.0)
        self.assertEqual(rice_item['unit'], 'g')
        self.assertEqual(rice_item['total_quantity'], 300.0)

    def test_calculate_shopping_cost_estimate(self):
        result = generate_shopping_list_from_meal_plan(
            self.account,
            date_start=self.meal_plan.date,
            date_end=self.meal_plan.date,
        )
        cost = calculate_shopping_cost_estimate(result['shopping_items'])

        self.assertIn('total_cost', cost)
        self.assertIn('items_with_cost', cost)
        self.assertGreater(cost['total_cost'], 0)
        self.assertEqual(len(cost['items_with_cost']), 2)

    def test_suggest_shopping_optimization(self):
        result = generate_shopping_list_from_meal_plan(
            self.account,
            date_start=self.meal_plan.date,
            date_end=self.meal_plan.date,
        )
        optimization = suggest_shopping_optimization(result['shopping_items'])

        self.assertIsInstance(optimization, dict)
        self.assertIn('suggestions', optimization)
        self.assertIn('optimization_tips', optimization)
        self.assertIsInstance(optimization['suggestions'], list)
        self.assertIsInstance(optimization['optimization_tips'], list)
