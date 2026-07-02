from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Set

from app.services.chat_text_service import normalize_chat_text, tokenize_chat_text


_GOAL_KEYWORDS: Dict[str, Set[str]] = {
    'greeting': {'hello', 'hi', 'hey', 'alo', 'chao', 'xin', 'bye'},
    'price': {'gia', 'bao', 'nhieu', 'price', 'cost', 'chi', 'phi', 'ton'},
    'meal_plan': {'meal_plan', 'menu', 'bua', 'sang', 'trua', 'toi', 'tuan', 'ngay'},
    'recipe': {'recipe', 'cach', 'lam', 'huong', 'dan', 'nau', 'cong', 'thuc', 'buoc'},
    'nutrition': {'nutrition', 'calo', 'kcal', 'protein', 'carb', 'fat', 'vitamin', 'dinh', 'duong'},
    'shopping': {'shopping', 'mua', 'sam', 'danh', 'sach', 'can'},
    'ingredient': {'ingredient', 'nguyen', 'lieu', 'thanh', 'phan'},
    'recommendation': {'recommendation', 'goi', 'y', 'nen', 'an', 'mon', 'phu', 'hop'},
    'budget': {'ngan', 'sach', 'budget', 're', 'tiet', 'kiem'},
}

_GOAL_PRIORITY: Sequence[str] = (
    'price',
    'meal_plan',
    'recipe',
    'nutrition',
    'shopping',
    'ingredient',
    'recommendation',
    'greeting',
    'budget',
)

_EXPECTED_TERMS: Dict[str, Set[str]] = {
    'greeting': {'xin chao', 'chao', 'hello', 'hi'},
    'price': {'gia', 'chi phi', 'tong', 'uoc tinh', 'khong co du lieu gia', 'vnd', 'dong'},
    'meal_plan': {'thuc don', 'bua', 'sang', 'trua', 'toi', 'ngay', 'menu'},
    'recipe': {'nguyen lieu', 'buoc', 'cach lam', 'huong dan', 'cong thuc', 'nau', 'lam', 'che bien', 'ga', 'thit', 'ca', 'rau', 'trung', 'tom', 'bo', 'heo', 'mon', 'com', 'canh', 'sup', 'chao', 'pho', 'bun', 'mien', 'banh', 'xao', 'chien', 'luoc', 'hap', 'kho', 'rang'},
    'nutrition': {'calo', 'kcal', 'protein', 'carb', 'fat', 'dinh duong'},
    'shopping': {'danh sach mua', 'shopping', 'can mua', 'nguyen lieu'},
    'ingredient': {'nguyen lieu', 'thanh phan', 'ingredient'},
    'recommendation': {'goi y', 'mon', 'nen an', 'phu hop'},
    'budget': {'ngan sach', 'chi phi', 'uoc tinh', 'tiet kiem'},
}

_DYNAMIC_GOALS = {'price', 'meal_plan', 'recipe', 'nutrition', 'shopping', 'ingredient', 'recommendation', 'budget'}

_TIME_SENSITIVE_MARKERS = {'hom nay', 'ngay mai', 'tuan nay', 'thang nay', 'today', 'tomorrow'}


def _contains_any_normalized(text: str, terms: Sequence[str]) -> bool:
    normalized_terms = [normalize_chat_text(term) for term in terms if term]
    return any(term and term in text for term in normalized_terms)


@dataclass
class RequestAnalysis:
    user_text: str
    normalized_text: str
    tokens: List[str]
    primary_goal: str
    detected_goals: List[str] = field(default_factory=list)
    expected_terms: List[str] = field(default_factory=list)
    skip_cache: bool = False
    is_time_sensitive: bool = False

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def analyze_user_request(user_text: str, intent_name: Optional[str] = None) -> RequestAnalysis:
    normalized = normalize_chat_text(user_text)
    tokens = tokenize_chat_text(user_text)
    token_set = set(tokens)

    detected: List[str] = []
    for goal in _GOAL_PRIORITY:
        keywords = _GOAL_KEYWORDS.get(goal, set())
        if token_set.intersection(keywords):
            detected.append(goal)

    normalized_intent = str(intent_name or '').strip().lower()
    if normalized_intent and normalized_intent not in detected:
        detected.insert(0, normalized_intent)

    primary_goal = normalized_intent or (detected[0] if detected else 'general')
    is_time_sensitive = any(marker in normalized for marker in _TIME_SENSITIVE_MARKERS)
    skip_cache = primary_goal in _DYNAMIC_GOALS or is_time_sensitive

    expected_terms = sorted(_EXPECTED_TERMS.get(primary_goal, set()))
    if primary_goal == 'general' and detected:
        expected_terms = sorted({
            term
            for goal in detected
            for term in _EXPECTED_TERMS.get(goal, set())
        })

    return RequestAnalysis(
        user_text=user_text,
        normalized_text=normalized,
        tokens=tokens,
        primary_goal=primary_goal,
        detected_goals=detected,
        expected_terms=expected_terms,
        skip_cache=skip_cache,
        is_time_sensitive=is_time_sensitive,
    )


def build_response_contract(analysis: RequestAnalysis) -> str:
    goal = analysis.primary_goal
    rules = [
        'Tra loi dung yeu cau moi nhat cua nguoi dung, khong lan man, khong chuyen chu de.',
        'Neu thieu du lieu thi noi ro phan nao thieu, khong tu suy dien thanh mot bai tra loi khac.',
    ]

    if goal == 'price':
        rules.append('Nguoi dung dang hoi gia/chi phi. Bat buoc tra loi bang gia, chi phi, uoc tinh hoac noi ro khong co du lieu gia.')
    elif goal == 'meal_plan':
        rules.append('Nguoi dung dang can thuc don. Bat buoc tra loi bang thuc don, bua an, hoac ket qua tao meal plan.')
    elif goal == 'recipe':
        rules.append('Nguoi dung dang can cong thuc. Bat buoc dua ra nguyen lieu, cach lam, hoac huong dan nau.')
    elif goal == 'nutrition':
        rules.append('Nguoi dung dang hoi dinh duong. Bat buoc tra loi bang thong tin dinh duong, kcal, protein, carb, fat, hoac giai thich dinh duong.')
    elif goal == 'shopping':
        rules.append('Nguoi dung dang can danh sach mua sam. Bat buoc tap trung vao nguyen lieu can mua.')
    elif goal == 'ingredient':
        rules.append('Nguoi dung dang hoi ve nguyen lieu. Bat buoc tap trung vao nguyen lieu/thanh phan lien quan.')
    elif goal == 'recommendation':
        rules.append('Nguoi dung dang can goi y. Bat buoc dua ra mon an phu hop va ly do ngan gon.')

    if analysis.is_time_sensitive:
        rules.append('Yeu cau co yeu to thoi gian. Uu tien boi canh hien tai, khong dung cau tra loi cache chung chung.')

    return '\n'.join(f'- {rule}' for rule in rules)


def validate_response_against_request(
    user_text: str,
    response_text: str,
    analysis: Optional[RequestAnalysis] = None,
    intent_name: Optional[str] = None,
) -> Dict[str, object]:
    analyzed = analysis or analyze_user_request(user_text, intent_name=intent_name)
    response = normalize_chat_text(response_text)
    issues: List[str] = []

    if not response:
        issues.append('empty_response')
    if any(marker in response for marker in ('query_sim', 'confidence', 'score')):
        issues.append('technical_leak')

    expected_terms = analyzed.expected_terms
    if expected_terms and not _contains_any_normalized(response, expected_terms):
        issues.append('missing_expected_terms')

    if analyzed.primary_goal == 'price':
        if not _contains_any_normalized(response, ('gia', 'chi phi', 'uoc tinh', 'khong co du lieu gia', 'dong', 'vnd')):
            issues.append('price_answer_missing')
    elif analyzed.primary_goal == 'meal_plan':
        if not _contains_any_normalized(response, ('thuc don', 'bua', 'sang', 'trua', 'toi', 'meal plan', 'menu')):
            issues.append('meal_plan_answer_missing')
    elif analyzed.primary_goal == 'recipe':
        if not _contains_any_normalized(response, ('nguyen lieu', 'buoc', 'cach lam', 'huong dan', 'cong thuc')):
            issues.append('recipe_answer_missing')
    elif analyzed.primary_goal == 'nutrition':
        if not _contains_any_normalized(response, ('calo', 'kcal', 'protein', 'carb', 'fat', 'dinh duong')):
            issues.append('nutrition_answer_missing')
    elif analyzed.primary_goal == 'shopping':
        if not _contains_any_normalized(response, ('danh sach mua', 'shopping', 'can mua', 'nguyen lieu')):
            issues.append('shopping_answer_missing')
    elif analyzed.primary_goal == 'ingredient':
        if not _contains_any_normalized(response, ('nguyen lieu', 'thanh phan', 'ingredient')):
            issues.append('ingredient_answer_missing')
    elif analyzed.primary_goal == 'recommendation':
        if not _contains_any_normalized(response, ('goi y', 'mon', 'phu hop', 'nen an')):
            issues.append('recommendation_answer_missing')

    if analyzed.primary_goal != 'general':
        unrelated_goals = [goal for goal in _EXPECTED_TERMS.keys() if goal not in {analyzed.primary_goal, 'budget'}]
        unrelated_hits = [
            goal for goal in unrelated_goals
            if goal != analyzed.primary_goal and _contains_any_normalized(response, _EXPECTED_TERMS.get(goal, set()))
        ]
        if unrelated_hits and not _contains_any_normalized(response, expected_terms):
            issues.append(f'unrelated_goal:{"|".join(sorted(unrelated_hits))}')

    return {
        'ok': not issues,
        'issues': issues,
        'analysis': analyzed.to_dict(),
    }
