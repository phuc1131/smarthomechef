from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.nutrition.models import FoodIngredient, Ingredient, Recipe


def parse_quantity_to_grams(quantity, unit):
    if quantity is None:
        return None
    try:
        q = Decimal(str(quantity))
    except (InvalidOperation, TypeError):
        import re

        match = re.search(r'([0-9]+(?:\.[0-9]+)?)', str(quantity))
        if not match:
            return None
        try:
            q = Decimal(match.group(1))
        except InvalidOperation:
            return None

    unit_text = (unit or '').strip().lower()
    if unit_text in {'g', 'gram', 'grams', 'gr'} or unit_text.endswith('g') and unit_text != 'kg':
        return q
    if unit_text in {'kg', 'kilogram', 'kilograms'}:
        return q * Decimal('1000')
    if unit_text in {'mg', 'milligram', 'milligrams'}:
        return q / Decimal('1000')
    if unit_text in {'ml', 'milliliter', 'milliliters'}:
        return None
    if unit_text in {'l', 'liter', 'litre', 'liters', 'litres'}:
        return None
    if unit_text in {
        'cai', 'cái', 'qua', 'quả', 'mieng', 'miếng', 'trai', 'trái',
        'bat', 'bát', 'chen', 'chén', 'muong', 'muỗng', 'thia', 'thìa',
        'cây', 'cay', 'vien', 'viên', 'hop', 'hộp', 'chai', 'goi', 'gói',
        'tui', 'túi', 'tách', 'tach', 'khoi', 'khối'
    }:
        return q * Decimal('50')
    return None


class Command(BaseCommand):
    help = (
        'Import FoodIngredient rows from Recipe.ingredients_json for recipes that already contain ingredient data.'
        ' This does not invent new ingredients for foods without existing Recipe ingredient data.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Do not write to the database; only print what would be created or updated.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        recipes = Recipe.objects.exclude(ingredients_json__isnull=True).exclude(ingredients_json__exact='')
        recipe_count = recipes.count()
        self.stdout.write(f'Found {recipe_count} recipes with ingredients_json data.')

        if recipe_count == 0:
            self.stdout.write('No recipe ingredient data available to import.')
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0
        missing_ingredient_count = 0
        missing_food_count = 0

        with transaction.atomic():
            for recipe in recipes.select_related('food'):
                if not recipe.food:
                    missing_food_count += 1
                    self.stdout.write(self.style.WARNING(f'Recipe {recipe.pk} has no linked Food. Skipping.'))
                    continue

                ingredients = recipe.ingredients_json or []
                if not isinstance(ingredients, list) or not ingredients:
                    skipped_count += 1
                    self.stdout.write(self.style.WARNING(f'Recipe {recipe.pk} has empty or invalid ingredients_json.'))
                    continue

                for ingredient_entry in ingredients:
                    if isinstance(ingredient_entry, dict):
                        raw_name = ingredient_entry.get('name')
                        quantity = ingredient_entry.get('quantity')
                        unit = ingredient_entry.get('unit')
                    else:
                        raw_name = str(ingredient_entry)
                        quantity = None
                        unit = None

                    if not raw_name:
                        skipped_count += 1
                        continue

                    raw_name = raw_name.strip()
                    ingredient = Ingredient.objects.filter(name__iexact=raw_name).first()
                    if not ingredient and not dry_run:
                        ingredient = Ingredient.objects.create(name=raw_name)
                        self.stdout.write(self.style.NOTICE(f'Created Ingredient: {raw_name}'))
                    elif not ingredient:
                        self.stdout.write(self.style.NOTICE(f'Ingredient missing (dry-run): {raw_name}'))

                    grams = parse_quantity_to_grams(quantity, unit)
                    if grams is None:
                        self.stdout.write(self.style.WARNING(
                            f'Skipping {recipe.food.name} -> {raw_name}: could not parse quantity={quantity} unit={unit}'
                        ))
                        skipped_count += 1
                        continue

                    if dry_run:
                        self.stdout.write(
                            f'[DRY RUN] FoodIngredient for {recipe.food.name} / {ingredient.name} = {grams}g'
                        )
                        continue

                    fi, created = FoodIngredient.objects.update_or_create(
                        food=recipe.food,
                        ingredient=ingredient,
                        defaults={'quantity_grams': grams},
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(
                            f'Created FoodIngredient: {recipe.food.name} -> {ingredient.name} ({grams}g)'
                        ))
                    else:
                        updated_count += 1
                        self.stdout.write(
                            f'Updated FoodIngredient: {recipe.food.name} -> {ingredient.name} ({grams}g)'
                        )

        self.stdout.write(self.style.SUCCESS(
            f'Import complete: {created_count} created, {updated_count} updated, {skipped_count} skipped, {missing_ingredient_count} missing ingredient names, {missing_food_count} recipes without food.'
        ))
