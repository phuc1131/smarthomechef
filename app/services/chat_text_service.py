import re
from typing import List, Tuple

_PHRASE_SYNONYM_REPLACEMENTS: List[Tuple[str, str]] = [
    (r'\b(thực đơn|thuc don|meal plan|menu)\b', 'meal_plan'),
    (r'\b(công thức|cong thuc|cách làm|cach lam)\b', 'recipe'),
    (r'\b(gợi ý|goi y|recommend|nên ăn|nen an|mon nao|món nào|món nao)\b', 'recommendation'),
    (r'\b(dinh dưỡng|dinh duong|calo|calories|nutrition)\b', 'nutrition'),
    (r'\b(mua sắm|mua sam|shopping list|shopping|cần mua|can mua)\b', 'shopping'),
    (r'\b(nguyên liệu|nguyen lieu|thành phần|thanh phan|ingredient)\b', 'ingredient'),
    (r'\b(phở|pho|bún|bun|mì|mi|hủ tiếu|hu tieu|mi quang|mi quang)\b', 'noodle'),
    (r'\b(món ăn|mon an|danh sách|danh sach)\b', 'dish'),
]


def _normalize_phrase_synonyms(text: str) -> str:
    for pattern, replacement in _PHRASE_SYNONYM_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.UNICODE)
    return text


def normalize_chat_text(text: str) -> str:
    if text is None:
        return ''
    normalized = text.strip().lower()
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r"[^\w\s'-]+", '', normalized, flags=re.UNICODE)
    normalized = _normalize_phrase_synonyms(normalized)
    return normalized


def tokenize_chat_text(text: str) -> List[str]:
    normalized = normalize_chat_text(text)
    if not normalized:
        return []
    return re.findall(r"[\w'-]+", normalized, flags=re.UNICODE)
