"""
Django management command để fill nutrition data cho Foods
python manage.py fill_nutrition_data --batch=20
"""

from django.core.management.base import BaseCommand
from django.db import models
from app.services.nutrition_data_service import NutritionDataFiller, LocalNutritionDatabase
from apps.nutrition.models import Food
from app.services.food_classifier_service import FoodClassifier


class Command(BaseCommand):
    help = 'Fill missing nutrition data for Foods from Spoonacular API or local database'
    
    def add_arguments(self, parser):
        parser.add_argument('--batch', type=int, default=10, help='Batch size to process')
        parser.add_argument('--force', action='store_true', help='Force refill even if data exists')
        parser.add_argument('--classify', action='store_true', help='Classify foods as ingredient vs food')
    
    def handle(self, *args, **options):
        batch_size = options['batch']
        force_refill = options['force']
        do_classify = options['classify']
        
        self.stdout.write(f"Processing batch size: {batch_size}")
        
        # Phase 1: Classify foods
        if do_classify:
            self.stdout.write("\n=== PHASE 1: CLASSIFY FOODS ===")
            self._classify_foods()
        
        # Phase 2: Fill nutrition data
        self.stdout.write("\n=== PHASE 2: FILL NUTRITION DATA ===")
        self._fill_nutrition_data(batch_size, force_refill)
    
    def _classify_foods(self):
        """Phân loại foods thành ingredient vs food"""
        foods = Food.objects.all()
        ingredient_count = 0
        food_count = 0
        unknown_count = 0
        
        for food in foods:
            nutrition_data = {
                'calories': food.calories,
                'protein': food.protein,
                'carbs': food.carbs,
                'fat': food.fat,
                'fiber': food.fiber,
                'vitamin_a': food.vitamin_a,
                'vitamin_c': food.vitamin_c,
                'calcium': food.calcium,
                'iron': food.iron,
            }
            
            classification = FoodClassifier.classify(food.name, nutrition_data)
            scores = FoodClassifier.get_confidence_score(food.name, nutrition_data)
            
            self.stdout.write(
                f"{food.name:30} -> {classification:12} "
                f"(ingredient: {scores['ingredient']:.2f}, food: {scores['food']:.2f}, unknown: {scores['unknown']:.2f})"
            )
            
            if classification == 'ingredient':
                ingredient_count += 1
            elif classification == 'food':
                food_count += 1
            else:
                unknown_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f"\nClassification Summary:\n"
            f"  Ingredients: {ingredient_count}\n"
            f"  Foods: {food_count}\n"
            f"  Unknown: {unknown_count}"
        ))
    
    def _fill_nutrition_data(self, batch_size: int, force_refill: bool):
        """Fill nutrition data cho foods"""
        if force_refill:
            query = Food.objects.all()[:batch_size]
            self.stdout.write(f"Force refilling nutrition data for {batch_size} foods...")
        else:
            query = Food.objects.filter(
                models.Q(calories__isnull=True) | 
                models.Q(protein__isnull=True) |
                models.Q(carbs__isnull=True) |
                models.Q(fat__isnull=True)
            )[:batch_size]
            self.stdout.write(f"Found {query.count()} foods with missing nutrition data")
        
        filled = 0
        failed = 0
        skipped = 0
        
        for food in query:
            # Check if already has nutrition
            if not force_refill and all([food.calories, food.protein, food.carbs, food.fat]):
                self.stdout.write(f"  [OK] {food.name} (already has data, skipping)")
                skipped += 1
                continue
            
            try:
                # Try local database first
                local_data = LocalNutritionDatabase.get_nutrition_data(food.name)
                if local_data:
                    NutritionDataFiller._apply_nutrition_data(food, local_data)
                    self.stdout.write(
                        self.style.SUCCESS(f"  [OK] {food.name} (filled from local DB)")
                    )
                    filled += 1
                    continue
                
                # Try Spoonacular API
                # self.stdout.write(f"  • {food.name} (searching API...)")
                # (Can enable if you want, but it's slow)
                # from app.services.nutrition_data_service import SpoonacularService
                # search_results = SpoonacularService.search_ingredient(food.name, number=1)
                # if search_results:
                #     ingredient_id = search_results[0].get('id')
                #     if SpoonacularService.fill_food_nutrition(food.id, ingredient_id):
                #         self.stdout.write(self.style.SUCCESS(f"  [OK] {food.name} (filled from API)"))
                #         filled += 1
                #     else:
                #         failed += 1
                # else:
                #     self.stdout.write(self.style.WARNING(f"  [ERROR] {food.name} (not found in API)"))
                #     failed += 1
                
                self.stdout.write(self.style.WARNING(f"  - {food.name} (not in local DB)"))
                failed += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  [ERROR] {food.name} (error: {e})"))
                failed += 1
        
        self.stdout.write(self.style.SUCCESS(
            f"\nNutrition Data Fill Summary:\n"
            f"  Filled: {filled}\n"
            f"  Skipped: {skipped}\n"
            f"  Failed: {failed}"
        ))
