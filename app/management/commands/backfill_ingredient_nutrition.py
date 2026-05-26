from datetime import datetime
import csv
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.nutrition.models import Ingredient, IngredientNutrition
from app.services.nutrition_data_service import NutritionDataFiller
from app.config import SPOONACULAR_RETRIES

ARTIFACT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'artifacts')
FAIL_CSV = os.path.join(ARTIFACT_PATH, 'failed_nutrition_backfill.csv')


class Command(BaseCommand):
    help = 'Backfill missing Ingredient nutrition (per 100g) using Spoonacular/Gemini/local DB'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=None, help='Limit number of ingredients to process')
        parser.add_argument('--batch-size', type=int, default=50, help='Batch size for each DB query')
        parser.add_argument('--no-spoonacular', action='store_true', help='Disable Spoonacular lookup')
        parser.add_argument('--no-gemini', action='store_true', help='Disable Gemini fallback')

    def handle(self, *args, **options):
        limit = options.get('limit')
        batch_size = options.get('batch_size') or 50
        use_spoonacular = not options.get('no_spoonacular')
        use_gemini = not options.get('no_gemini')

        os.makedirs(ARTIFACT_PATH, exist_ok=True)
        if not os.path.exists(FAIL_CSV):
            with open(FAIL_CSV, 'w', newline='', encoding='utf-8') as fh:
                writer = csv.writer(fh)
                writer.writerow(['timestamp', 'ingredient_id', 'ingredient_name', 'error', 'attempts'])

        qs = Ingredient.objects.all().order_by('id')
        # Find ingredients that either have no nutrition row or zeros
        missing = []
        for ing in qs:
            try:
                nut = IngredientNutrition.objects.filter(ingredient=ing).first()
                if not nut:
                    missing.append(ing.id)
                else:
                    # check macros
                    if (not nut.calories or nut.calories == 0) and (not nut.protein or nut.protein == 0):
                        missing.append(ing.id)
            except Exception:
                missing.append(ing.id)

        if limit:
            missing = missing[:limit]

        total = len(missing)
        self.stdout.write(self.style.SUCCESS(f'Found {total} ingredients missing nutrition'))

        processed = 0
        failed = 0
        for start in range(0, total, batch_size):
            batch_ids = missing[start:start + batch_size]
            ingredients = list(Ingredient.objects.filter(id__in=batch_ids).order_by('id'))
            for ing in ingredients:
                processed += 1
                self.stdout.write(f'[{processed}/{total}] Backfilling: {ing.id} - {ing.name}')
                try:
                    ok = NutritionDataFiller.fill_missing_ingredient_nutrition(
                        ing,
                        use_spoonacular=use_spoonacular,
                        use_gemini=use_gemini,
                    )
                    if not ok:
                        failed += 1
                        with open(FAIL_CSV, 'a', newline='', encoding='utf-8') as fh:
                            writer = csv.writer(fh)
                            writer.writerow([datetime.utcnow().isoformat(), ing.id, ing.name, 'not_filled', SPOONACULAR_RETRIES])
                except Exception as exc:
                    failed += 1
                    with open(FAIL_CSV, 'a', newline='', encoding='utf-8') as fh:
                        writer = csv.writer(fh)
                        writer.writerow([datetime.utcnow().isoformat(), ing.id, ing.name, str(exc), SPOONACULAR_RETRIES])

        self.stdout.write(self.style.SUCCESS(f'Done: processed={processed} failed={failed}'))
