"""
Backfill personalization data from legacy tables to new models.
Usage: python manage.py shell < tools/maintenance/backfill_personalization_data.py
"""

import os
import sys
import django
from decimal import Decimal
from datetime import date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

from apps.users.models import Account, UserBudget, UserHealthGoal
from apps.core_models.models import MealRecommendation
from apps.nutrition.models import Food, Recipe
from django.db.models import Q

def backfill_user_budgets():
    """Create default budgets for all active users."""
    print("=" * 60)
    print("BACKFILL: User Budgets")
    print("=" * 60)
    
    accounts = Account.objects.filter(is_active=True)
    created_count = 0
    
    for account in accounts:
        # Create default daily budget if doesn't exist
        budget, is_new = UserBudget.objects.get_or_create(
            account=account,
            budget_period='daily',
            defaults={
                'budget_amount': Decimal('200000'),  # Default 200k VND/day
                'currency': 'VND',
                'is_active': True,
            }
        )
        if is_new:
            created_count += 1
            print(f"  [OK] Created budget for {account.username} - {budget.budget_amount} VND/day")
    
    print(f"\nSummary: {created_count} budgets created")
    print(f"   Total users: {len(accounts)}")
    return created_count


def backfill_user_health_goals():
    """Create default health goals for users without any."""
    print("\n" + "=" * 60)
    print("BACKFILL: User Health Goals")
    print("=" * 60)
    
    accounts = Account.objects.filter(is_active=True)
    created_count = 0
    
    for account in accounts:
        # Create default 'maintain' health goal if doesn't exist
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
            print(f"  [OK] Created health goal for {account.username}")
    
    print(f"\nSummary: {created_count} health goals created")
    print(f"   Total users: {len(accounts)}")
    return created_count


def backfill_meal_recommendations():
    """Generate initial meal recommendations based on existing meal plans."""
    print("\n" + "=" * 60)
    print("BACKFILL: Meal Recommendations")
    print("=" * 60)
    
    # Get recipes with ratings
    recipes = Recipe.objects.filter(is_verified=True)
    accounts = Account.objects.filter(is_active=True)
    created_count = 0
    
    # Create basic recommendations for each user
    for account in accounts[:10]:  # Limit to first 10 users for safety
        for recipe in recipes[:5]:  # Create 5 recommendations per user
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
    
    print(f"  [OK] Created recommendations for users")
    print(f"\nSummary: {created_count} recommendations created")
    return created_count


def main():
    """Run all backfill operations."""
    print("\n🔄 PERSONALIZATION DATA BACKFILL")
    print("=" * 60)
    print(f"Timestamp: {date.today()}")
    
    try:
        budgets = backfill_user_budgets()
        goals = backfill_user_health_goals()
        recommendations = backfill_meal_recommendations()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] BACKFILL COMPLETE")
        print("=" * 60)
        print(f"Total changes:")
        print(f"   • User Budgets: {budgets}")
        print(f"   • Health Goals: {goals}")
        print(f"   • Recommendations: {recommendations}")
        print(f"   • TOTAL: {budgets + goals + recommendations}")
        
    except Exception as e:
        print(f"\n[ERROR] ERROR during backfill: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
