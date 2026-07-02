"""
Database-first handlers for price, ingredient-cost, recipe-cost, and budget meal queries.

Nguyên tắc:
- Giá chỉ được lấy từ IngredientPrice.
- Chi phí món chỉ được tính từ FoodIngredient + IngredientPrice.
- AI chỉ dùng để diễn giải ở lớp ngoài, không được tự đoán giá.
"""

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple, cast

from django.db.models import Q

from apps.nutrition.models import Food, FoodIngredient, Ingredient, IngredientAlias, IngredientPrice, UnitConversion
from apps.users.models import UserDisease, UserGoal, UserPreferenceProfile, UserProfile


PRICE_QUERY = 'PRICE_QUERY'
INGREDIENT_COST_QUERY = 'INGREDIENT_COST_QUERY'
RECIPE_COST_QUERY = 'RECIPE_COST_QUERY'
BUDGET_MEAL_PLAN = 'BUDGET_MEAL_PLAN'
GENERAL_MEAL_PLAN = 'GENERAL_MEAL_PLAN'
SHOPPING_LIST_BY_BUDGET = 'SHOPPING_LIST_BY_BUDGET'
NUTRITION_ADVICE = 'NUTRITION_ADVICE'
UNKNOWN = 'UNKNOWN'

_MASS_UNITS = {'g', 'gram', 'grams', 'gr', 'kg', 'kilogram', 'kilograms'}
_VOLUME_UNITS = {'ml', 'milliliter', 'milliliters', 'l', 'liter', 'liters'}
_COUNT_UNITS = {'cai', 'cái', 'qua', 'quả', 'trai', 'trái', 'bo', 'bó', 'hop', 'hộp', 'goi', 'gói'}
_UNIT_PATTERN = r'kg|g|gram|grams|gr|ml|l|cái|cai|quả|qua|trái|trai|bó|bo|hộp|hop|gói|goi'


def _normalize_text(text: str) -> str:
    text = (text or '').strip().lower()
    if not text:
        return ''
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r'[^a-z0-9\s/.,-]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0')


def _lookup_key(text: str) -> str:
    return _normalize_text(text).replace(' ', '_')


def _lookup_tokens(text: str) -> List[str]:
    return [token for token in _normalize_text(text).replace('_', ' ').split() if token]


def _split_goal_value(value: str) -> List[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return []
    normalized = normalized.replace('_', ' ')
    parts = [normalized]
    parts.extend(token for token in normalized.split() if len(token) > 2)
    return list(dict.fromkeys(parts))


def _build_account_goal_context(account=None) -> Dict:
    context_terms = []
    goal_codes = set()
    if not account:
        return {'terms': [], 'goal_codes': set()}

    profile = UserProfile.objects.filter(account=account).first()
    if profile:
        for value in [profile.health_goal, profile.medical_conditions, profile.dietary_preferences]:
            context_terms.extend(_split_goal_value(value or ''))

    for goal in UserGoal.objects.filter(account=account):
        goal_code = _normalize_text(getattr(goal, 'goal_type', '') or '').replace(' ', '_')
        if goal_code:
            goal_codes.add(goal_code)
            context_terms.extend(_split_goal_value(goal_code))

    diseases = UserDisease.objects.filter(account=account).select_related('disease')
    for user_disease in diseases:
        disease_name = getattr(getattr(user_disease, 'disease', None), 'name', '') or ''
        context_terms.extend(_split_goal_value(disease_name))

    preferences = UserPreferenceProfile.objects.filter(account=account).first()
    if preferences:
        for field_name in ['preferred_keywords', 'avoided_keywords', 'preferred_categories']:
            values = getattr(preferences, field_name, None) or []
            if isinstance(values, list):
                for value in values:
                    context_terms.extend(_split_goal_value(str(value)))

    ordered_terms = list(dict.fromkeys(term for term in context_terms if term))
    return {'terms': ordered_terms, 'goal_codes': goal_codes}


def classify_food_price_intent(text: str, account=None) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return UNKNOWN

    price_keywords = ['gia', 'bao nhieu tien', 'bao nhieu', 'chi phi', 'ton bao nhieu', 'cost', 'price', 'budget', 'ngan sach', 'mua duoc']
    meal_keywords = ['thuc don', 'menu', 'lap thuc don', 'an gi', 'bua sang', 'bua trua', 'bua toi', '7 ngay', 'tuan', 'ngay']
    disease_keywords = ['cam lanh', 'om', 'benh', 'sot', 'ho', 'met', 'khoe']
    goal_context = _build_account_goal_context(account)
    dynamic_goal_terms = goal_context['terms']

    has_budget_amount = bool(re.search(r'\d+(?:[.,]\d+)?\s*(k|nghin|ngan|trieu|vnd|d)(?:\s*/\s*ngay)?', normalized))
    has_price = any(re.search(rf'\b{keyword}\b', normalized) for keyword in price_keywords) or has_budget_amount
    if has_price and re.search(r'\b(gia|price|cost)\b', normalized) and len(normalized.split()) <= 4:
        return PRICE_QUERY
    has_meal = any(re.search(rf'\b{keyword}\b', normalized) for keyword in meal_keywords)
    has_quantity_list = bool(re.search(rf'\d+(?:[.,]\d+)?\s*(?:{_UNIT_PATTERN})\s+[a-z0-9]', normalized))
    has_recipe_words = any(keyword in normalized for keyword in ['mon', 'nau', 'khau phan', 'cho 2 nguoi', 'cho 4 nguoi'])
    has_recipe_food_name = normalized.startswith('mon ') or ' mon ' in normalized
    has_shopping = 'mua duoc nhung gi' in normalized or ('mua duoc' in normalized and has_budget_amount)
    has_dynamic_goal_match = any(re.search(rf'\b{term}\b', normalized) for term in dynamic_goal_terms)
    has_disease = any(re.search(rf'\b{keyword}\b', normalized) for keyword in disease_keywords)

    if has_price and has_meal:
        return BUDGET_MEAL_PLAN
    if has_shopping:
        return SHOPPING_LIST_BY_BUDGET
    if has_price and has_quantity_list:
        return INGREDIENT_COST_QUERY
    if has_price and (has_recipe_words or has_recipe_food_name):
        return RECIPE_COST_QUERY
    if has_dynamic_goal_match or has_disease:
        return NUTRITION_ADVICE
    if has_meal:
        return GENERAL_MEAL_PLAN
    if has_price:
        return PRICE_QUERY
    return UNKNOWN


def _clean_query_tokens(text: str) -> str:
    normalized = _normalize_text(text)
    noise = [
        'gia', 'bao nhieu', 'bao nhieu tien', 'chi phi', 'ton bao nhieu', 'mua', 'het',
        'hom nay', 'winmart', 'price', 'cost', 'budget', 'ngan sach', 'mon', 'nau',
        'cho', 'nguoi', 'khoang', 'thuc don', 'lap', 'menu', 'duoi', 'tren',
    ]
    for token in noise:
        normalized = re.sub(rf'\b{token}\b', ' ', normalized)
    normalized = re.sub(r'\d+(?:[.,]\d+)?\s*(?:k|nghin|ngan|trieu|vnd|d|' + _UNIT_PATTERN + r')', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip(' ,.-')


def _find_ingredient_candidates(name: str, limit: int = 5) -> List[Ingredient]:
    normalized = _normalize_text(name)
    if not normalized:
        return []

    lookup_key = _lookup_key(name)
    lookup_variants = list(dict.fromkeys(
        variant for variant in [
            normalized,
            lookup_key,
            normalized.replace('thit ', '').strip() if normalized.startswith('thit ') else '',
            lookup_key.replace('thit_', '').strip('_') if lookup_key.startswith('thit_') else '',
        ]
        if variant
    ))

    direct = list(
        Ingredient.objects.filter(is_deleted=False).filter(
            Q(normalized_name__in=lookup_variants)
            | Q(normalized_name__icontains=lookup_key)
            | Q(normalized_name__icontains=normalized)
        ).order_by('name')[:limit]
    )
    if direct:
        return direct

    exact = list(
        Ingredient.objects.filter(is_deleted=False).filter(
            Q(name__iexact=name.strip())
            | Q(name__iexact=normalized)
            | Q(name__icontains=name.strip())
            | Q(name__icontains=normalized)
        ).order_by('name')[:limit]
    )
    if exact:
        return exact

    alias_matches = []
    try:
        alias_rows = list(
            IngredientAlias.objects.filter(
                is_deleted=False,
            ).filter(
                Q(alias__iexact=name.strip())
                | Q(alias__iexact=normalized)
                | Q(alias__icontains=name.strip())
                | Q(alias__icontains=normalized)
                | Q(alias__iexact=lookup_key)
            ).select_related('ingredient')[:limit]
        )
    except Exception:
        alias_rows = []
    for row in alias_rows:
        if row.ingredient and not row.ingredient.is_deleted:
            alias_matches.append(row.ingredient)
    if alias_matches:
        return alias_matches

    try:
        alias_rows = list(
            IngredientAlias.objects.filter(
                Q(alias__iexact=normalized)
                | Q(alias__iexact=lookup_key)
                | Q(alias__icontains=normalized)
                | Q(alias__icontains=lookup_key)
            ).select_related('ingredient')[:limit]
        )
    except Exception:
        alias_rows = []
    if alias_rows:
        return [row.ingredient for row in alias_rows if row.ingredient and not row.ingredient.is_deleted]

    contains = list(
        Ingredient.objects.filter(is_deleted=False).filter(
            Q(name__icontains=name.strip())
            | Q(name__icontains=normalized)
            | Q(normalized_name__icontains=lookup_key)
            | Q(normalized_name__icontains=normalized)
        ).order_by('name')[:limit]
    )
    if contains:
        return contains

    token_candidates = []
    query_tokens = set(_lookup_tokens(name))
    for ingredient in Ingredient.objects.filter(is_deleted=False).only('id', 'name', 'normalized_name'):
        ing_name = (ingredient.normalized_name or _normalize_text(ingredient.name)).replace('_', ' ')
        ing_tokens = set(_lookup_tokens(ing_name))
        score = SequenceMatcher(None, normalized, ing_name).ratio()
        overlap = len(query_tokens & ing_tokens)
        if query_tokens and overlap == len(query_tokens):
            score += 0.45
        elif overlap:
            score += 0.12 * overlap
        if normalized in ing_name or ing_name in normalized or lookup_key in (ingredient.normalized_name or ''):
            score += 0.25
        if score >= 0.45 or overlap:
            token_candidates.append((overlap, score, ingredient))
    token_candidates.sort(key=lambda item: (-item[0], -item[1], item[2].name))
    return [ingredient for _, _, ingredient in token_candidates[:limit]]


def find_best_ingredient_match(name: str) -> Optional[Ingredient]:
    candidates = _find_ingredient_candidates(name, limit=1)
    return candidates[0] if candidates else None


def find_similar_ingredients(name: str, limit: int = 5) -> List[str]:
    return [ingredient.name for ingredient in _find_ingredient_candidates(name, limit=limit)]


def get_latest_ingredient_price(ingredient: Ingredient) -> Optional[IngredientPrice]:
    if not ingredient:
        return None
    return IngredientPrice.objects.filter(ingredient=ingredient).order_by('-updated_at', '-id').first()


def _lookup_db_conversion_factor(ingredient: Optional[Ingredient], from_unit: str) -> Optional[Decimal]:
    if not ingredient or not from_unit:
        return None
    try:
        row = UnitConversion.objects.filter(
            ingredient=ingredient,
            from_unit__iexact=from_unit,
        ).order_by('-id').first()
    except Exception:
        return None
    if not row:
        return None
    return _to_decimal(row.conversion_factor)


def _quantity_in_price_unit(quantity: Decimal, request_unit: str, price_unit: str, ingredient: Optional[Ingredient] = None) -> Optional[Decimal]:
    request_unit = _normalize_text(request_unit)
    price_unit = _normalize_text(price_unit)
    quantity = _to_decimal(quantity)
    if quantity <= 0:
        return None
    if request_unit == price_unit:
        return quantity

    if request_unit in _MASS_UNITS and price_unit in _MASS_UNITS:
        grams = quantity * Decimal('1000') if request_unit == 'kg' else quantity
        return grams / Decimal('1000') if price_unit == 'kg' else grams

    if request_unit in _VOLUME_UNITS and price_unit in _VOLUME_UNITS:
        milliliters = quantity * Decimal('1000') if request_unit == 'l' else quantity
        return milliliters / Decimal('1000') if price_unit == 'l' else milliliters

    if request_unit in _COUNT_UNITS and price_unit in _COUNT_UNITS:
        return quantity

    factor = _lookup_db_conversion_factor(ingredient, request_unit)
    if factor:
        base_quantity = quantity * factor
        if price_unit == 'kg':
            return base_quantity / Decimal('1000')
        if price_unit in {'g', 'gram', 'grams', 'gr', 'ml', 'l'}:
            return base_quantity
        return base_quantity

    return None


def _price_cost_for_quantity(ingredient: Ingredient, quantity: Decimal, request_unit: str) -> Optional[Dict]:
    price_obj = get_latest_ingredient_price(ingredient)
    if not price_obj or price_obj.price_per_unit is None:
        return None

    ingredient_obj = cast(Ingredient, ingredient)
    converted_quantity = _quantity_in_price_unit(quantity, request_unit, price_obj.unit_type, ingredient=ingredient_obj)
    if converted_quantity is None:
        return None

    total_cost = converted_quantity * _to_decimal(price_obj.price_per_unit)
    return {
        'ingredient': ingredient,
        'price_obj': price_obj,
        'requested_quantity': float(quantity),
        'requested_unit': request_unit,
        'converted_quantity': float(converted_quantity),
        'cost': float(total_cost),
    }


def extract_ingredient_names_from_question(text: str) -> List[str]:
    cleaned = _clean_query_tokens(text)
    if not cleaned:
        return []
    separators = re.split(r',| va | và | voi | với ', cleaned)
    names = []
    for item in separators:
        candidate = item.strip(' .,-')
        if candidate:
            names.append(candidate)
    return names


def extract_ingredient_quantity_items(text: str) -> List[Dict]:
    normalized = _normalize_text(text)
    segments = re.split(r',| va | và ', normalized)
    items = []
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
        match = re.search(rf'(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>{_UNIT_PATTERN})\s+(?P<name>.+)$', segment)
        if not match:
            match = re.search(rf'(?P<name>.+?)\s+(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>{_UNIT_PATTERN})$', segment)
        if not match:
            continue
        quantity = _to_decimal(match.group('qty').replace(',', '.'))
        unit = match.group('unit')
        name = match.group('name').strip(' .,-')
        if quantity > 0 and name:
            items.append({
                'ingredient_name': name,
                'quantity': quantity,
                'unit': unit,
            })
    return items


def get_ingredient_prices(ingredient_names: List[str], limit: int = 10) -> Dict:
    found = []
    not_found = []
    suggestions = {}

    for ing_name in ingredient_names:
        ingredient = find_best_ingredient_match(ing_name)
        if not ingredient:
            not_found.append(ing_name)
            similar = find_similar_ingredients(ing_name)
            if similar:
                suggestions[ing_name] = similar
            continue

        price_obj = get_latest_ingredient_price(ingredient)
        if not price_obj:
            not_found.append(ingredient.name)
            continue

        found.append({
            'ingredient_name': ingredient.name,
            'ingredient_id': getattr(ingredient, 'pk', None),
            'price_per_unit': float(price_obj.price_per_unit),
            'unit_type': price_obj.unit_type,
            'updated_at': price_obj.updated_at.isoformat() if price_obj.updated_at else None,
        })

    return {
        'found': found[:limit],
        'not_found': not_found,
        'suggestions': suggestions,
        'total_found': len(found),
    }


def format_price_info_for_ai(price_data: Dict) -> str:
    if not price_data.get('found'):
        return 'Không có dữ liệu giá từ database cho các nguyên liệu này.'

    lines = ['DỮ LIỆU GIÁ NGUYÊN LIỆU TỪ DATABASE:']
    for item in price_data['found']:
        lines.append(
            f"- {item['ingredient_name']}: {item['price_per_unit']:,.0f} VNĐ/{item['unit_type']} "
            f"(cập nhật: {item.get('updated_at') or 'N/A'})"
        )

    if price_data.get('not_found'):
        lines.append('Chưa có dữ liệu giá cho:')
        for ing_name in price_data['not_found']:
            lines.append(f'- {ing_name}')

    return '\n'.join(lines)


def get_ai_price_context(user_question: str) -> Optional[str]:
    if classify_food_price_intent(user_question) not in {PRICE_QUERY, INGREDIENT_COST_QUERY, RECIPE_COST_QUERY}:
        return None
    ing_names = extract_ingredient_names_from_question(user_question)
    if not ing_names:
        return None
    return format_price_info_for_ai(get_ingredient_prices(ing_names))


def calculate_recipe_cost(food: Food, servings: float = 1.0) -> Dict:
    servings_decimal = _to_decimal(servings or 1)
    ingredients = list(FoodIngredient.objects.filter(food=food).select_related('ingredient').order_by('-quantity_grams'))
    details = []
    total_cost = Decimal('0')
    missing_price_ingredients = []
    missing_primary_price = False

    for index, food_ingredient in enumerate(ingredients):
        ingredient = food_ingredient.ingredient
        quantity_grams = _to_decimal(food_ingredient.quantity_grams) * servings_decimal
        price_obj = get_latest_ingredient_price(ingredient)
        if not price_obj or price_obj.price_per_unit is None:
            missing_price_ingredients.append(ingredient.name)
            if index < 2 or quantity_grams >= Decimal('80'):
                missing_primary_price = True
            continue

        converted_quantity = _quantity_in_price_unit(quantity_grams, 'g', price_obj.unit_type, ingredient=ingredient)
        if converted_quantity is None:
            missing_price_ingredients.append(ingredient.name)
            if index < 2 or quantity_grams >= Decimal('80'):
                missing_primary_price = True
            continue

        ingredient_cost = converted_quantity * _to_decimal(price_obj.price_per_unit)
        total_cost += ingredient_cost
        details.append({
            'ingredient_name': ingredient.name,
            'quantity_grams': float(quantity_grams),
            'price_per_unit': float(price_obj.price_per_unit),
            'unit_type': price_obj.unit_type,
            'cost': float(ingredient_cost),
        })

    return {
        'food': food,
        'servings': float(servings_decimal),
        'details': details,
        'total_cost': float(total_cost) if total_cost > 0 else None,
        'cost_per_serving': float(total_cost / servings_decimal) if total_cost > 0 and servings_decimal > 0 else None,
        'missing_price_ingredients': missing_price_ingredients,
        'missing_primary_price': missing_primary_price,
        'has_ingredient_details': bool(ingredients),
    }


def _find_best_food_match(text: str) -> Optional[Food]:
    cleaned = _clean_query_tokens(text)
    if not cleaned:
        return None

    exact = Food.objects.filter(name__iexact=cleaned).order_by('name').first()
    if exact:
        return exact

    contains = list(Food.objects.filter(name__icontains=cleaned).order_by('name')[:5])
    if contains:
        return max(contains, key=lambda food: len(food.name or ''))

    normalized_query = _normalize_text(cleaned)
    best_match = None
    best_score = Decimal('0')
    for food in Food.objects.only('id', 'name', 'normalized_name'):
        normalized_name = food.normalized_name or _normalize_text(food.name)
        ratio = Decimal(str(SequenceMatcher(None, normalized_query, normalized_name).ratio()))
        if normalized_query in normalized_name or normalized_name in normalized_query:
            ratio += Decimal('0.2')
        if ratio > best_score:
            best_score = ratio
            best_match = food
    if best_score >= Decimal('0.45'):
        return best_match
    return None


def _format_single_price_answer(ingredient: Ingredient, price_obj: IngredientPrice) -> str:
    return (
        f'Giá {ingredient.name} hiện có trong hệ thống là khoảng {float(price_obj.price_per_unit):,.0f}đ/{price_obj.unit_type}.\n'
        'Nguồn dữ liệu: bảng giá nguyên liệu đã crawl từ WinMart.\n'
        f'Thời gian cập nhật: {price_obj.updated_at:%Y-%m-%d %H:%M}.\n'
        'Nếu cần, mình có thể dùng mức giá này để tính chi phí món ăn hoặc lập thực đơn theo ngân sách.'
    )


def handle_single_ingredient_price_query(text: str) -> Dict:
    ingredient_names = extract_ingredient_names_from_question(text)
    if not ingredient_names:
        return {'success': False, 'intent': PRICE_QUERY, 'response': 'Bạn muốn hỏi giá nguyên liệu nào?'}

    ingredient = find_best_ingredient_match(ingredient_names[0])
    if not ingredient:
        similar = find_similar_ingredients(ingredient_names[0])
        if similar:
            return {
                'success': False,
                'intent': PRICE_QUERY,
                'response': f'Hệ thống chưa tìm thấy nguyên liệu chính xác. Bạn có muốn chọn một trong các nguyên liệu gần giống này không: {", ".join(similar)}?',
            }
        return {
            'success': False,
            'intent': PRICE_QUERY,
            'response': f'Hiện hệ thống chưa có dữ liệu nguyên liệu "{ingredient_names[0]}" trong database.',
        }

    price_obj = get_latest_ingredient_price(ingredient)
    if not price_obj:
        return {
            'success': False,
            'intent': PRICE_QUERY,
            'response': f'Hiện hệ thống chưa có giá của {ingredient.name} trong database.',
        }

    return {
        'success': True,
        'intent': PRICE_QUERY,
        'response': _format_single_price_answer(ingredient, price_obj),
    }


def handle_multi_ingredient_cost_query(text: str) -> Dict:
    items = extract_ingredient_quantity_items(text)
    if not items:
        return {
            'success': False,
            'intent': INGREDIENT_COST_QUERY,
            'response': 'Mình chưa tách được danh sách nguyên liệu và số lượng. Bạn có thể ghi theo dạng "500g thịt bò, 1kg rau cải, 10 quả trứng" không?',
        }

    details = []
    total_cost = Decimal('0')
    missing = []
    for item in items:
        ingredient = find_best_ingredient_match(item['ingredient_name'])
        if not ingredient:
            missing.append(item['ingredient_name'])
            continue
        cost_info = _price_cost_for_quantity(ingredient, item['quantity'], item['unit'])
        if not cost_info:
            missing.append(ingredient.name)
            continue
        total_cost += _to_decimal(cost_info['cost'])
        details.append(cost_info)

    if not details:
        return {
            'success': False,
            'intent': INGREDIENT_COST_QUERY,
            'response': 'Hiện hệ thống chưa đủ dữ liệu giá để tính chính xác danh sách nguyên liệu này từ database.',
        }

    lines = ['Chi phí ước tính từ dữ liệu giá nguyên liệu trong database:']
    for detail in details:
        lines.append(
            f"- {detail['ingredient'].name}: {detail['requested_quantity']:g}{detail['requested_unit']} = {detail['cost']:,.0f}đ"
        )
    lines.append(f'Tổng chi phí ước tính: {float(total_cost):,.0f}đ.')
    if missing:
        lines.append(f'Lưu ý: chưa tính được cho {", ".join(missing)} vì thiếu dữ liệu giá hoặc quy đổi đơn vị trong database.')

    return {
        'success': True,
        'intent': INGREDIENT_COST_QUERY,
        'response': '\n'.join(lines),
        'missing_items': missing,
        'total_cost': float(total_cost),
    }


def handle_recipe_cost_query(text: str) -> Dict:
    food = _find_best_food_match(text)
    if not food:
        return {
            'success': False,
            'intent': RECIPE_COST_QUERY,
            'response': 'Hiện hệ thống chưa tìm thấy món ăn phù hợp trong database để tính chi phí chính xác.',
        }

    servings_match = re.search(r'cho\s+(\d+)\s+nguoi', _normalize_text(text))
    servings = float(servings_match.group(1)) if servings_match else 1.0
    cost_info = calculate_recipe_cost(food, servings=servings)

    if not cost_info['has_ingredient_details']:
        return {
            'success': False,
            'intent': RECIPE_COST_QUERY,
            'response': f'Món {food.name} hiện chưa có công thức nguyên liệu trong database nên chưa thể tính chi phí chuẩn.',
        }

    if cost_info['total_cost'] is None:
        return {
            'success': False,
            'intent': RECIPE_COST_QUERY,
            'response': f'Món {food.name} hiện chưa đủ dữ liệu giá nguyên liệu trong database để tính chi phí chính xác.',
        }

    lines = [f'Món {food.name} có chi phí ước tính khoảng {cost_info["total_cost"]:,.0f}đ cho {int(servings)} khẩu phần.']
    lines.append('Chi tiết:')
    for detail in cost_info['details']:
        lines.append(
            f"- {detail['ingredient_name']}: {detail['quantity_grams']:,.0f}g × {detail['price_per_unit']:,.0f}đ/{detail['unit_type']} = {detail['cost']:,.0f}đ"
        )
    if cost_info['cost_per_serving'] is not None:
        lines.append(f'Chi phí mỗi khẩu phần: {cost_info["cost_per_serving"]:,.0f}đ.')
    if cost_info['missing_price_ingredients']:
        lines.append(
            'Lưu ý: chi phí có thể chưa hoàn toàn đầy đủ vì thiếu giá của '
            + ', '.join(cost_info['missing_price_ingredients'])
            + '.'
        )

    return {
        'success': True,
        'intent': RECIPE_COST_QUERY,
        'response': '\n'.join(lines),
        'food_id': food.id,
        'total_cost': cost_info['total_cost'],
        'missing_primary_price': cost_info['missing_primary_price'],
    }


def get_all_ingredient_prices() -> List[Dict]:
    prices = []
    for price_obj in IngredientPrice.objects.select_related('ingredient').all():
        prices.append({
            'ingredient_name': price_obj.ingredient.name,
            'ingredient_id': getattr(price_obj.ingredient, 'pk', None),
            'price_per_unit': float(price_obj.price_per_unit),
            'unit_type': price_obj.unit_type,
            'updated_at': price_obj.updated_at.isoformat() if price_obj.updated_at else None,
        })
    return prices
