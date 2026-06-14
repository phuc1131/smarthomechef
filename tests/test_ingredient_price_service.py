from decimal import Decimal

from django.test import TestCase

from apps.nutrition.models import Food, FoodCategory, FoodIngredient, Ingredient, IngredientPrice
from app.services.ingredient_price_service import (
    BUDGET_MEAL_PLAN,
    INGREDIENT_COST_QUERY,
    PRICE_QUERY,
    RECIPE_COST_QUERY,
    classify_food_price_intent,
    handle_multi_ingredient_cost_query,
    handle_recipe_cost_query,
    handle_single_ingredient_price_query,
)
from app.services.meal_plan_generator_service import MealPlanGeneratorService


class IngredientPriceServiceTests(TestCase):
    def test_classify_food_price_intent_matches_md_flow(self):
        self.assertEqual(classify_food_price_intent('Giá ức gà bao nhiêu?'), PRICE_QUERY)
        self.assertEqual(
            classify_food_price_intent('Mua 500g thịt bò và 1kg rau cải hết bao nhiêu?'),
            INGREDIENT_COST_QUERY,
        )
        self.assertEqual(
            classify_food_price_intent('Món gà xào nấm tốn bao nhiêu tiền?'),
            RECIPE_COST_QUERY,
        )
        self.assertEqual(
            classify_food_price_intent('Lập thực đơn 7 ngày với 500k'),
            BUDGET_MEAL_PLAN,
        )

    def test_handle_single_ingredient_price_query_reads_database(self):
        ingredient = Ingredient.objects.create(name='Ức gà', normalized_name='uc ga')
        IngredientPrice.objects.create(ingredient=ingredient, price_per_unit=Decimal('89000'), unit_type='kg')

        result = handle_single_ingredient_price_query('Giá ức gà bao nhiêu?')

        self.assertTrue(result['success'])
        self.assertIn('89,000đ/kg', result['response'])
        self.assertIn('WinMart', result['response'])

    def test_handle_multi_ingredient_cost_query_sums_database_prices(self):
        beef = Ingredient.objects.create(name='Thịt bò', normalized_name='thit bo')
        greens = Ingredient.objects.create(name='Rau cải', normalized_name='rau cai')
        IngredientPrice.objects.create(ingredient=beef, price_per_unit=Decimal('250000'), unit_type='kg')
        IngredientPrice.objects.create(ingredient=greens, price_per_unit=Decimal('30000'), unit_type='kg')

        result = handle_multi_ingredient_cost_query('Mua 500g thịt bò và 1kg rau cải hết bao nhiêu?')

        self.assertTrue(result['success'])
        self.assertAlmostEqual(result['total_cost'], 155000.0, places=2)
        self.assertIn('155,000đ', result['response'])

    def test_handle_recipe_cost_query_uses_food_ingredients_and_price_table(self):
        category = FoodCategory.objects.create(name='Món chính')
        food = Food.objects.create(name='Gà xào nấm', normalized_name='ga xao nam', category=category)
        chicken = Ingredient.objects.create(name='Ức gà', normalized_name='uc ga')
        mushroom = Ingredient.objects.create(name='Nấm', normalized_name='nam')
        FoodIngredient.objects.create(food=food, ingredient=chicken, quantity_grams=Decimal('300'))
        FoodIngredient.objects.create(food=food, ingredient=mushroom, quantity_grams=Decimal('200'))
        IngredientPrice.objects.create(ingredient=chicken, price_per_unit=Decimal('89000'), unit_type='kg')
        IngredientPrice.objects.create(ingredient=mushroom, price_per_unit=Decimal('75000'), unit_type='kg')

        result = handle_recipe_cost_query('Món gà xào nấm tốn bao nhiêu tiền?')

        self.assertTrue(result['success'])
        self.assertAlmostEqual(result['total_cost'], 41700.0, places=2)
        self.assertIn('Gà xào nấm', result['response'])
        self.assertIn('41,700đ', result['response'])

    def test_meal_plan_budget_context_splits_daily_and_meal_budget(self):
        budget = MealPlanGeneratorService._resolve_budget_context(
            'Lập thực đơn 7 ngày với 500k',
            {'profile_data': {}},
            7,
        )

        self.assertTrue(budget['has_budget'])
        self.assertAlmostEqual(budget['total_budget'], 500000.0, places=2)
        self.assertAlmostEqual(budget['daily_budget'], 500000.0 / 7, places=2)
        self.assertAlmostEqual(
            budget['meal_budgets']['breakfast'],
            budget['daily_budget'] * 0.25,
            places=2,
        )
