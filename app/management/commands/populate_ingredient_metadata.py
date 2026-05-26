from django.core.management.base import BaseCommand

from apps.nutrition.models import Ingredient
from services.food_data_service import (
    get_or_fetch_ingredient,
    sync_ingredient_aliases_and_nutrition,
)


class Command(BaseCommand):
    help = (
        'Sync Ingredient alias and nutrition metadata using Gemini and Spoonacular APIs.'
        ' Use --ingredient to process one ingredient, or --all to process every ingredient.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--ingredient',
            type=str,
            help='Tên nguyên liệu cụ thể cần đồng bộ.',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Đồng bộ tất cả nguyên liệu hiện có trong bảng Ingredient.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Giới hạn số nguyên liệu khi dùng --all.',
        )
        parser.add_argument(
            '--no-gemini',
            action='store_false',
            dest='use_gemini',
            help='Không dùng Gemini để sinh alias.',
        )
        parser.add_argument(
            '--no-spoonacular',
            action='store_false',
            dest='use_spoonacular',
            help='Không dùng Spoonacular để fetch dinh dưỡng.',
        )

    def handle(self, *args, **options):
        ingredient_name = options.get('ingredient')
        use_gemini = options.get('use_gemini', True)
        use_spoonacular = options.get('use_spoonacular', True)
        limit = options.get('limit', 0)

        ingredients = []
        if ingredient_name:
            ingredient = get_or_fetch_ingredient(ingredient_name)
            if ingredient:
                ingredients = [ingredient]
        elif options.get('all'):
            query = Ingredient.objects.all().order_by('name')
            if limit > 0:
                query = query[:limit]
            ingredients = list(query)
        else:
            self.stderr.write('Please provide --ingredient or --all')
            return

        if not ingredients:
            self.stdout.write('No ingredients to process.')
            return

        for index, ingredient in enumerate(ingredients, start=1):
            self.stdout.write(f'[{index}/{len(ingredients)}] Syncing {ingredient.name}')
            result = sync_ingredient_aliases_and_nutrition(
                ingredient.name,
                use_gemini=use_gemini,
                use_spoonacular=use_spoonacular,
            )
            if not result.get('success'):
                self.stderr.write(f"Failed: {result.get('message')}")
                continue

            alias_count = len(result.get('aliases') or [])
            nutrition_saved = 'yes' if result.get('nutrition') else 'no'
            self.stdout.write(
                f"  - Aliases saved: {alias_count} | Nutrition saved: {nutrition_saved}"
            )
