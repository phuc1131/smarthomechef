import pytest

from services.recipe_variations_service import (
    generate_recipe_variations,
    suggest_substitutes,
    get_ingredient_category,
    get_substitution_warnings,
)


@pytest.mark.parametrize('ingredient', ['sữa', 'bơ', 'phô mai', 'nước mắm', 'trứng'])
def test_suggest_substitutes_returns_list(ingredient):
    subs = suggest_substitutes(ingredient)
    assert isinstance(subs, list)


@pytest.mark.parametrize('ingredient', ['sữa', 'bơ', 'phô mai', 'nước mắm', 'trứng'])
def test_get_ingredient_category_nonempty(ingredient):
    category = get_ingredient_category(ingredient)
    assert category is not None


@pytest.mark.parametrize('available,missing', [
    (['trứng', 'thịt heo', 'cơm'], ['nước mắm', 'hành']),
    (['cơm'], ['nước', 'muối', 'dầu ăn', 'nguyên liệu khác']),
])
def test_get_substitution_warnings_structure(available, missing):
    result = get_substitution_warnings(available, missing)
    assert isinstance(result, dict)
    assert 'can_make_recipe' in result
    assert 'warnings' in result


@pytest.mark.parametrize('case', [
    {'recipe': 'Cơm trứng thịt heo', 'available': ['trứng', 'thịt heo', 'cơm'], 'missing': ['dầu ăn', 'nước mắm']},
    {'recipe': 'Canh tôm cà chua', 'available': ['nước', 'cà chua'], 'missing': ['tôm', 'muối']},
])
def test_generate_recipe_variations_structure(case):
    result = generate_recipe_variations(case['recipe'], case['available'], case['missing'])
    assert isinstance(result, dict)
    assert 'variations' in result
    assert isinstance(result['variations'], list)
