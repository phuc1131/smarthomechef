# Wrapper layer for backward compatibility - all implementation moved to apps.meal_plans.views
from apps.meal_plans.views import meal_plans, meal_plan_add, meal_plan_delete

__all__ = ['meal_plans', 'meal_plan_add', 'meal_plan_delete']