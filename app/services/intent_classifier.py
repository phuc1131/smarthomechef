"""Lightweight intent classifier prototype.

This is a safe, dependency-free starter implementation that uses
normalized token and phrase matching to produce an (intent, confidence).
It is intended as a drop-in that can later be upgraded to a transformer
or embedding-based classifier.
"""
import re
from typing import Tuple

from .chat_text_service import normalize_chat_text, tokenize_chat_text


_INTENT_KEYWORDS = {
    "meal_plan": [
        ("thuc don", 3.0), ("thực đơn", 3.0), ("meal plan", 3.0), ("menu", 2.0),
        ("lap thuc don", 2.5), ("lập thực đơn", 2.5), ("ke hoach an", 2.0), ("kế hoạch ăn", 2.0),
        ("ăn gì cho tuần", 2.0), ("an gi cho tuan", 2.0), ("ăn gì cho ngày", 2.0), ("an gi cho ngay", 2.0),
        ("50k", 2.5), ("100k", 2.5), ("ngan sach", 2.5), ("ngân sách", 2.5),
        ("tiet kiem", 2.0), ("tiết kiệm", 2.0), ("re tien", 2.0), ("rẻ tiền", 2.0),
    ],
    "recipe": [
        ("cong thuc", 2.5), ("cách làm", 2.5), ("cach lam", 2.5), ("recipe", 2.5),
        ("huong dan nau", 2.0), ("hướng dẫn nấu", 2.0), ("nấu như thế nào", 2.0),
        ("nau nhu the nao", 2.0), ("cach che bien", 2.0), ("cách chế biến", 2.0),
        ("lam mon", 2.0), ("làm món", 2.0), ("nau mon", 2.0), ("nấu món", 2.0),
    ],
    "recommendation": [
        ("goi y", 2.0), ("gợi ý", 2.0), ("recommend", 2.0), ("gợi ý món", 2.5),
        ("gợi ý món ăn", 2.5), ("nen an", 2.0), ("nên ăn", 2.0), ("an gi ngon", 2.0),
        ("ăn gì ngon", 2.0), ("tim mon", 2.0), ("tìm món", 2.0), ("chon mon", 2.0), ("chọn món", 2.0),
    ],
    "nutrition": [
        ("dinh duong", 2.0), ("dinh dưỡng", 2.0), ("calo", 1.5), ("calories", 1.5),
        ("nutrition", 2.0), ("protein", 1.5), ("carb", 1.0), ("fat", 1.0),
        ("thanh phan", 1.5), ("thành phần", 1.5), ("bao nhieu calo", 2.0), ("bao nhiêu calo", 2.0),
        ("tom tat", 2.5), ("tóm tắt", 2.5), ("nhat ky", 2.5), ("nhật ký", 2.5), ("da an", 2.0), ("đã ăn", 2.0),
    ],
    "shopping": [
        ("mua sam", 2.0), ("mua sắm", 2.0), ("shopping list", 2.5), ("shopping", 2.0),
        ("can mua", 2.0), ("cần mua", 2.0), ("di cho", 2.5), ("đi chợ", 2.5),
        ("danh sach mua", 2.0), ("danh sách mua", 2.0),
    ],
    "ingredient": [
        ("nguyen lieu", 2.0), ("nguyên liệu", 2.0), ("thành phần", 1.5), ("thanh phan", 1.5),
        ("ingredient", 2.0), ("co nhung gi", 1.5), ("có những gì", 1.5),
        ("gom nhung gi", 1.5), ("gồm những gì", 1.5),
    ],
    "greeting": [
        ("chao", 1.0), ("chào", 1.0), ("hello", 1.0), ("hi", 1.0), ("alo", 1.0),
        ("allo", 1.0), ("hey", 1.0), ("xin chao", 1.5), ("xin chào", 1.5),
    ],
}

_DISH_NAME_PATTERNS = [
    (r"\bgà rán\b", "gà rán"),
    (r"\bga ran\b", "gà rán"),
    (r"\bthịt kho\b", "thịt kho"),
    (r"\bthit kho\b", "thịt kho"),
    (r"\bcá chiên\b", "cá chiên"),
    (r"\bca chien\b", "cá chiên"),
    (r"\bcanh chua\b", "canh chua"),
    (r"\bphở\b", "phở"),
]


def classify_intent(text: str) -> Tuple[str, float, list]:
    """[CLASSIFY] Keyword + dish name detection."""
    if not text:
        return "unknown", 0.0, []

    normalized = normalize_chat_text(text)
    tokens = set(tokenize_chat_text(text))

    has_dish_name = any(re.search(p, text, re.IGNORECASE) for p, _ in _DISH_NAME_PATTERNS)

    best_label = "unknown"
    best_score = 0.0
    best_matches = []

    for label, kws_weighted in _INTENT_KEYWORDS.items():
        matches = []
        current_score = 0.0
        max_possible_score = sum(w for _, w in kws_weighted)

        for kw, weight in kws_weighted:
            if kw in normalized or kw in tokens:
                matches.append(kw)
                current_score += weight

        score = current_score / max(1, max_possible_score)
        if any(len(m.split()) > 1 for m in matches):
            score *= 1.2

        if score > best_score:
            best_score = score
            best_label = label
            best_matches = matches

    if has_dish_name and best_label == "unknown":
        best_label = "recipe"
        best_matches = ["dish_name"]
        best_score = 0.6

    confidence = round(min(1.0, float(best_score * 2)), 3)
    return best_label, confidence, best_matches


def extract_dish_name(text: str) -> str:
    """Extract specific dish name from user query."""
    if not text:
        return ""
    for pattern, dish_name in _DISH_NAME_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return dish_name
    return ""
