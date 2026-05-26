"""
Test Food Classifier Bot
python manage.py test tests.test_food_classifier
"""

import pytest
from django.test import TestCase
from decimal import Decimal

from app.services.food_classifier_service import FoodClassifier, NutritionDataValidator


class FoodClassifierTestCase(TestCase):
    """Test Food Classifier Bot"""
    
    def test_classify_ingredient_by_keyword(self):
        """Test phân loại nguyên liệu qua keyword"""
        test_cases = [
            ('muối', 'ingredient'),
            ('baking powder', 'ingredient'),
            ('đường', 'ingredient'),
            ('gia vị', 'ingredient'),
            ('nước mắm', 'ingredient'),
            ('dầu ăn', 'ingredient'),
        ]
        
        for name, expected in test_cases:
            result = FoodClassifier.classify(name)
            print(f"{name:20} -> {result:15} (expected: {expected})")
            self.assertEqual(result, expected)
    
    def test_classify_food_by_keyword(self):
        """Test phân loại đồ ăn qua keyword"""
        test_cases = [
            ('cơm trắng', 'food'),
            ('mì gói', 'food'),
            ('rau xanh', 'food'),
            ('thịt gà', 'food'),
            ('cá tươi', 'food'),
            ('salad', 'food'),
        ]
        
        for name, expected in test_cases:
            result = FoodClassifier.classify(name)
            print(f"{name:20} -> {result:15} (expected: {expected})")
            self.assertEqual(result, expected)
    
    def test_classify_by_nutrition(self):
        """Test phân loại qua nutrition data"""
        # Ingredient: NO calories, HAS vitamins
        ingredient_nutrition = {
            'calories': 0,
            'protein': 0,
            'carbs': 0,
            'fat': 0,
            'vitamin_a': 100,
            'calcium': 50,
        }
        result = FoodClassifier.classify('unknown ingredient', ingredient_nutrition)
        self.assertEqual(result, 'ingredient')
        
        # Food: HAS calories + macros
        food_nutrition = {
            'calories': 150,
            'protein': 20,
            'carbs': 30,
            'fat': 5,
            'vitamin_a': 0,
        }
        result = FoodClassifier.classify('unknown food', food_nutrition)
        self.assertEqual(result, 'food')
    
    def test_confidence_scores(self):
        """Test confidence score calculation"""
        scores = FoodClassifier.get_confidence_score('muối')
        print(f"Scores for 'muối': {scores}")
        self.assertGreater(scores['ingredient'], scores['food'])
        self.assertGreater(scores['ingredient'], scores['unknown'])
        
        scores = FoodClassifier.get_confidence_score('cơm')
        print(f"Scores for 'cơm': {scores}")
        self.assertGreater(scores['food'], scores['ingredient'])
    
    def test_nutrition_validator(self):
        """Test nutrition data validator"""
        # Valid nutrition
        valid_data = {
            'calories': 150,
            'protein': 20,
            'carbs': 30,
            'fat': 5,
        }
        self.assertTrue(NutritionDataValidator.is_valid(valid_data))
        
        # Invalid nutrition (calories too high)
        invalid_data = {
            'calories': 5000,  # Unrealistic
            'protein': 20,
        }
        self.assertFalse(NutritionDataValidator.is_valid(invalid_data))
    
    def test_missing_fields(self):
        """Test find missing nutrition fields"""
        data = {
            'calories': 150,
            'protein': 20,
        }
        missing = NutritionDataValidator.get_missing_fields(data)
        print(f"Missing fields: {missing}")
        self.assertIn('carbs', missing)
        self.assertIn('fat', missing)
        self.assertIn('fiber', missing)
    
    def test_macro_validation(self):
        """Test macro calorie calculation"""
        # Valid: calories = 4*protein + 4*carbs + 9*fat
        valid = NutritionDataValidator.estimate_from_macros(
            calories=230,  # 4*20 + 4*30 + 9*5 = 80 + 120 + 45 = 245
            protein=20,
            carbs=30,
            fat=5
        )
        print(f"Macro validation: {valid}")
        # Should be close
    
    def test_classify_muoi(self):
        """Test muối classification"""
        nutrition = {
            'calories': 0,
            'protein': 0,
            'carbs': 0,
            'fat': 0,
            'sodium': 38758,  # Very high
            'calcium': 1040,
        }
        result = FoodClassifier.classify('muối', nutrition)
        self.assertEqual(result, 'ingredient')
    
    def test_classify_com(self):
        """Test cơm classification"""
        nutrition = {
            'calories': 130,
            'protein': 2.7,
            'carbs': 28,
            'fat': 0.3,
            'fiber': 0.4,
        }
        result = FoodClassifier.classify('cơm trắng', nutrition)
        self.assertEqual(result, 'food')


class LocalNutritionDatabaseTestCase(TestCase):
    """Test Local Nutrition Database"""
    
    def test_get_ingredient_data(self):
        """Test getting ingredient data"""
        from app.services.nutrition_data_service import LocalNutritionDatabase
        
        data = LocalNutritionDatabase.get_nutrition_data('muối')
        print(f"Muối data: {data}")
        self.assertEqual(data['type'], 'ingredient')
        self.assertEqual(data['calories'], 0)
        self.assertGreater(data['sodium'], 1000)
    
    def test_get_food_data(self):
        """Test getting food data"""
        from app.services.nutrition_data_service import LocalNutritionDatabase
        
        data = LocalNutritionDatabase.get_nutrition_data('cơm')
        print(f"Cơm data: {data}")
        self.assertEqual(data['type'], 'food')
        self.assertGreater(data['calories'], 0)
        self.assertGreater(data['protein'], 0)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
