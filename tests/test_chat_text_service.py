import pytest

from app.services.chat_text_service import normalize_chat_text, tokenize_chat_text


def test_normalize_chat_text_replaces_intent_synonyms():
    text = 'Tôi muốn lập thực đơn cho tuần tới'
    normalized = normalize_chat_text(text)

    assert 'meal_plan' in normalized
    assert 'thực đơn' not in normalized


def test_tokenize_chat_text_uses_canonical_tokens():
    tokens = tokenize_chat_text('Cho tôi công thức phở bò')

    assert 'recipe' in tokens
    assert 'noodle' in tokens
    assert 'phở' not in tokens
    assert 'bún' not in tokens


def test_shopping_and_nutrition_synonyms():
    assert 'shopping' in tokenize_chat_text('cần mua nguyên liệu cho món bún')
    assert 'nutrition' in tokenize_chat_text('Tư vấn dinh dưỡng cho người giảm cân')
