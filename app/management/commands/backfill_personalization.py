"""
Management command to backfill personalization data.
Usage: python manage.py backfill_personalization
"""

from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.users.models import Account
from apps.users.personalization_models import UserBudget, UserHealthGoal
from apps.core_models.ai_learning_models import MealRecommendation
from apps.nutrition.models import Recipe


class Command(BaseCommand):
    help = 'Backfill personalization data from legacy tables to new models'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("🔄 PERSONALIZATION DATA BACKFILL"))
        self.stdout.write("=" * 60)

        budgets_created = self._backfill_user_budgets()
        goals_created = self._backfill_user_health_goals()
        recommendations_created = self._backfill_meal_recommendations()

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("[SUCCESS] BACKFILL COMPLETE"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total changes:")
        self.stdout.write(f"   • User Budgets: {budgets_created}")
        self.stdout.write(f"   • Health Goals: {goals_created}")
        self.stdout.write(f"   • Recommendations: {recommendations_created}")
        self.stdout.write(f"   • TOTAL: {budgets_created + goals_created + recommendations_created}\n")

    def _backfill_user_budgets(self):
        """Create default budgets for all active users."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("BACKFILL: User Budgets")
        self.stdout.write("=" * 60)

        accounts = Account.objects.filter(is_active=True)
        created_count = 0

        for account in accounts:
            budget, is_new = UserBudget.objects.get_or_create(
                account=account,
                budget_period='daily',
                defaults={
                    'budget_amount': Decimal('200000'),
                    'currency': 'VND',
                    'is_active': True,
                }
            )
            if is_new:
                created_count += 1
                self.stdout.write(f"  [OK] Created budget for {account.username}")

        self.stdout.write(f"\nSummary: {created_count} budgets created")
        return created_count

    def _backfill_user_health_goals(self):
        """Create default health goals for users without any."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("BACKFILL: User Health Goals")
        self.stdout.write("=" * 60)

        accounts = Account.objects.filter(is_active=True)
        created_count = 0

        for account in accounts:
            goal, is_new = UserHealthGoal.objects.get_or_create(
                account=account,
                goal_type='maintain',
                defaults={
                    'target_macros': {'protein': 30, 'carbs': 50, 'fat': 20},
                    'is_active': True,
                }
            )
            if is_new:
                created_count += 1
                self.stdout.write(f"  [OK] Created health goal for {account.username}")

        self.stdout.write(f"\nSummary: {created_count} health goals created")
        return created_count

    def _backfill_meal_recommendations(self):
        """Generate initial meal recommendations based on existing recipes."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("BACKFILL: Meal Recommendations")
        self.stdout.write("=" * 60)

        accounts = Account.objects.filter(is_active=True)
        recipes = Recipe.objects.all()
        created_count = 0

        for account in accounts[:10]:
            for recipe in recipes[:3]:
                rec, is_new = MealRecommendation.objects.get_or_create(
                    account=account,
                    recipe=recipe,
                    defaults={
                        'score': Decimal('0.75'),
                        'match_score': Decimal('0.80'),
                        'budget_score': Decimal('0.70'),
                        'health_score': Decimal('0.75'),
                        'reason': 'Auto-generated from recipe verification',
                    }
                )
                if is_new:
                    created_count += 1

        self.stdout.write(f"  [OK] Created recommendations for users")
        self.stdout.write(f"\nSummary: {created_count} recommendations created")
        return created_count
