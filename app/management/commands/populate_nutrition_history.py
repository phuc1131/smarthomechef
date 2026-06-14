from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from apps.nutrition.models import Food, NutritionLog
from apps.users.models import Account


class Command(BaseCommand):
    help = 'Populate nutrition history for all users for the last N days.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of past days to generate history for (default: 30).'
        )
        parser.add_argument(
            '--meals-per-day',
            type=int,
            default=3,
            help='Meals per day to generate (default: 3).'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Generate entries even if logs already exist for the day.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without saving to the database.'
        )

    def handle(self, *args, **options):
        days = options['days']
        meals_per_day = options['meals_per_day']
        force = options['force']
        dry_run = options['dry_run']

        meal_types = ['Bữa sáng', 'Bữa trưa', 'Bữa tối']
        if meals_per_day <= 0:
            self.stderr.write('Meals per day phải lớn hơn 0.')
            return

        meal_types = meal_types[:meals_per_day] if meals_per_day <= len(meal_types) else meal_types + [f'Bữa phụ {i}' for i in range(1, meals_per_day - len(meal_types) + 1)]
        today = date.today()
        start_date = today - timedelta(days=days - 1)

        foods_qs = Food.objects.filter(
            calories__isnull=False,
            protein__isnull=False,
            carbs__isnull=False,
            fat__isnull=False,
        )
        if not foods_qs.exists():
            foods_qs = Food.objects.all()

        foods = list(foods_qs)
        if not foods:
            self.stderr.write('Không tìm thấy Food nào trong database để tạo NutritionLog.')
            return

        accounts = Account.objects.filter(is_active=True)
        if not accounts.exists():
            self.stderr.write('Không tìm thấy user nào để tạo dữ liệu.')
            return

        random.seed(2026)

        self.stdout.write(f'Generating nutrition history for {accounts.count()} users from {start_date} to {today}.')
        self.stdout.write(f'Using {len(foods)} foods; meals per day: {meals_per_day}.')

        created_count = 0
        skipped_count = 0

        for account in accounts:
            existing_days = set(
                NutritionLog.objects.filter(account=account, date__gte=start_date).values_list('date', flat=True)
            )
            for day_offset in range(days):
                current_day = start_date + timedelta(days=day_offset)
                if not force and current_day in existing_days:
                    skipped_count += meals_per_day
                    continue

                # If logs exist for the day and force is not set, skip the whole day.
                if not force and NutritionLog.objects.filter(account=account, date=current_day).exists():
                    skipped_count += meals_per_day
                    continue

                for meal_index, meal_type in enumerate(meal_types, start=1):
                    food = random.choice(foods)
                    servings = Decimal(random.choice([0.5, 0.75, 1, 1.25, 1.5, 2]))
                    total_calories = (food.calories or Decimal('0')) * servings
                    total_protein = (food.protein or Decimal('0')) * servings
                    total_carbs = (food.carbs or Decimal('0')) * servings
                    total_fat = (food.fat or Decimal('0')) * servings

                    if dry_run:
                        self.stdout.write(
                            f'[DRY RUN] account={account.username} date={current_day} meal={meal_type} '
                            f'food={food.name} servings={servings} calories={total_calories}'
                        )
                        continue

                    NutritionLog.objects.create(
                        account=account,
                        food=food,
                        date=current_day,
                        meal_type=meal_type,
                        servings=servings,
                        total_calories=total_calories,
                        total_protein=total_protein,
                        total_carbs=total_carbs,
                        total_fat=total_fat,
                    )
                    created_count += 1

        if dry_run:
            self.stdout.write('Dry run complete. No records were saved.')
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Nutrition history generation complete. Created {created_count} nutrition logs.'
            ))
            if skipped_count:
                self.stdout.write(self.style.WARNING(
                    f'Skipped approximately {skipped_count} entries because data already existed.'
                ))
