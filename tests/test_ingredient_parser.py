import pytest

from services.ingredient_parser_service import parse_ingredients_from_text

TEST_CASES = [
    "Tôi có trứng, thịt heo, hành",
    "Làm cháo từ gạo, gà và hành tây",
    "Tôi có cá hồi, cà chua, hành lá",
    "Có những thứ: trứng gà, thịt lợn, tỏi, nước mắm",
    "Bây giờ tôi lấy bơ, sữa, phô mai từ tủ lạnh",
    "Không có gì hết",
]


@pytest.mark.parametrize("text", TEST_CASES)
def test_parse_ingredients_returns_structure(text):
    result = parse_ingredients_from_text(text)
    assert isinstance(result, dict)
    assert 'success' in result
    assert 'ingredients' in result
    assert 'method' in result
    assert 'confidence' in result
