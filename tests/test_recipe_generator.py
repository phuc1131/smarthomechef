import pytest

pytestmark = pytest.mark.django_db

from services.recipe_generator_service import (
    recommend_recipes_from_ingredients,
    generate_recipe_details,
    _calculate_recipe_complexity,
)

TEST_INGREDIENTS = [
    ["trứng", "thịt heo", "hành", "cơm"],
    ["cá hồi", "cà chua", "hành lá", "dầu ăn"],
    ["gạo", "gà", "hành"],
]


@pytest.mark.parametrize("ingredients", TEST_INGREDIENTS)
def test_recommend_recipes_returns_structure(ingredients):
    result = recommend_recipes_from_ingredients(ingredients, limit=5)
    assert isinstance(result, dict)
    assert 'recipes' in result
    assert isinstance(result['recipes'], list)


def test_calculate_recipe_complexity_outputs():
    difficulty, confidence = _calculate_recipe_complexity(['trứng', 'cơm'])
    assert difficulty in {'easy', 'medium', 'hard'}
    assert isinstance(confidence, float)
