from typing import Optional

from apps.nutrition.models import Food, Ingredient, IngredientNutrition


def get_or_fetch_food(food_name: str) -> Optional[Food]:
    if not food_name:
        return None
    food_name = food_name.strip()
    if not food_name:
        return None

    food = Food.objects.filter(name__iexact=food_name).first()
    if food:
        return food

    food = Food.objects.filter(name__icontains=food_name).order_by('name').first()
    return food


def get_or_fetch_ingredient(ingredient_name: str) -> Optional[Ingredient]:
    if not ingredient_name:
        return None
    ingredient_name = ingredient_name.strip()
    if not ingredient_name:
        return None

    ingredient = Ingredient.objects.filter(name__iexact=ingredient_name, is_deleted=False).first()
    if ingredient:
        return ingredient

    ingredient = Ingredient.objects.filter(name__icontains=ingredient_name, is_deleted=False).order_by('name').first()
    if ingredient:
        return ingredient

    ingredient = Ingredient.objects.create(name=ingredient_name)
    return ingredient


def ensure_ingredient_nutrition(ingredient: Optional[Ingredient], default_nutrition: Optional[dict] = None) -> Optional[IngredientNutrition]:
    if ingredient is None:
        return None

    nutrition, _ = IngredientNutrition.objects.get_or_create(
        ingredient=ingredient,
        defaults={
            'calories': default_nutrition.get('calories', 0) if default_nutrition else 0,
            'protein': default_nutrition.get('protein', 0) if default_nutrition else 0,
            'carbs': default_nutrition.get('carbs', 0) if default_nutrition else 0,
            'fat': default_nutrition.get('fat', 0) if default_nutrition else 0,
            'fiber': default_nutrition.get('fiber', 0) if default_nutrition else 0,
        },
    )
    return nutrition
