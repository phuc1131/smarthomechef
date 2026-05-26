"""
Module tạo meal plan (thực đơn) thông minh dựa trên profile user.

Mục đích:
- Phân tích request từ user (health, budget, preferences, general meal plan)
- Lấy dữ liệu user (health goals, diseases, dietary preferences, avoided foods, budget)
- Query DB để tìm foods phù hợp dựa trên:
  * Health conditions (diabetes friendly, weight loss friendly)
  * Dietary preferences
  * Budget limit
  * Avoided keywords
  * Category preferences
- Nếu không đủ foods từ DB → call Spoonacular/Gemini API để tìm thêm
- Lập thực đơn (breakfast, lunch, dinner, snack)
- Lưu vào MealPlan

GHI NHỚ:
- Luôn lấy dữ liệu từ DB, không dùng dữ liệu cứng
- Cá nhân hóa dựa trên bệnh lý, lịch sử ăn, ngân sách của user
- Fallback API nếu DB không đủ
"""

import json
import re
import unicodedata
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q

from apps.users.models import Account, UserProfile, UserGoal, UserDisease, UserPreferenceProfile
from apps.nutrition.models import (
    Food,
    FoodIngredient,
    Ingredient,
    IngredientAlias,
    IngredientNutrition,
    IngredientPrice,
    NutritionLog,
    FoodCategory,
)
from apps.meal_plans.models import MealPlan
from app.services.external_apis import _gemini_generate_text, AI_AVAILABLE
from app.services.food_data_service import get_or_fetch_ingredient
from app.services.nutrition_data_service import NutritionDataFiller
from app.services.personalization_service import rank_food_candidates


class MealPlanGeneratorService:
    """Service tạo meal plan thông minh."""
    
    MEAL_TYPES = {
        'breakfast': ('Bữa sáng', 300, 500),        # 300-500 kcal
        'lunch': ('Bữa trưa', 600, 800),             # 600-800 kcal
        'dinner': ('Bữa tối', 500, 700),             # 500-700 kcal
        'snack': ('Bữa phụ', 100, 200),              # 100-200 kcal
    }
    
    @staticmethod
    def analyze_request(request_text):
        """
        Phân tích yêu cầu từ user để xác định loại request.
        
        Return: dict {
            'type': 'health' | 'budget' | 'diet' | 'general',
            'keywords': [list of keywords],
            'priority': 'urgent' | 'normal' | 'flexible',
            'constraints': {...}
        }
        """
        request_lower = request_text.lower()
        
        # Phân loại request
        if any(word in request_lower for word in ['bệnh', 'tiểu đường', 'huyết áp', 'mỡ máu', 'dị ứng', 'hen suyễn']):
            request_type = 'health'
        elif any(word in request_lower for word in ['tiền', 'ngân sách', 'rẻ', 'tối thiểu', 'giá']):
            request_type = 'budget'
        elif any(word in request_lower for word in ['chay', 'ăn chay', 'kiêng', 'không ăn', 'kiêng cữ']):
            request_type = 'diet'
        else:
            request_type = 'general'
        
        return {
            'type': request_type,
            'keywords': request_lower.split(),
            'priority': 'normal',
            'original_request': request_text,
        }
    
    @staticmethod
    def get_user_context(account):
        """Lấy toàn bộ dữ liệu user từ DB."""
        profile = UserProfile.objects.filter(account=account).first()
        goals = UserGoal.objects.filter(account=account)
        diseases = UserDisease.objects.filter(account=account).select_related('disease')
        preferences = UserPreferenceProfile.objects.filter(account=account).first()
        
        # Lấy lịch sử ăn 7 ngày gần nhất để phân tích xu hướng
        recent_logs = NutritionLog.objects.filter(
            account=account,
            date__gte=date.today() - timedelta(days=7)
        ).select_related('food')
        
        return {
            'account': account,
            'profile': profile,
            'goals': list(goals),
            'diseases': [ud.disease.name for ud in diseases],
            'preferences': preferences,
            'recent_food_ids': [log.food_id for log in recent_logs],
            'profile_data': {
                'age': profile.age if profile else None,
                'weight': float(profile.weight) if profile and profile.weight else None,
                'health_goal': profile.health_goal if profile else None,
                'medical_conditions': profile.medical_conditions if profile else None,
                'dietary_preferences': profile.dietary_preferences if profile else None,
                'budget_limit': float(profile.budget_limit) if profile and profile.budget_limit else None,
            }
        }
    
    @staticmethod
    def build_food_filter(user_context, request_type):
        """
        Xây dựng filter query để tìm foods phù hợp dựa trên user context.
        
        Return: Q object filter
        """
        profile = user_context['profile']
        goals = user_context['goals']
        diseases = user_context['diseases']
        preferences = user_context['preferences']
        
        # Base filter: chỉ lấy foods có dữ liệu hợp lệ
        q_filter = Q(name__isnull=False)
        
        # Health-based filters
        diseases_list = [d.lower() for d in user_context['diseases']]
        
        if any('tiểu đường' in d or 'diabetes' in d for d in diseases_list):
            q_filter &= Q(is_diabetes_friendly=True)
        
        if goals and any(g.goal_type == 'weight_loss' for g in goals):
            q_filter &= Q(is_weight_loss_friendly=True)
        
        # Dietary preferences - loại bỏ foods không phù hợp
        if preferences and preferences.avoided_keywords:
            avoided = preferences.avoided_keywords if isinstance(preferences.avoided_keywords, list) else []
            for keyword in avoided:
                q_filter &= ~Q(name__icontains=keyword)
                q_filter &= ~Q(description__icontains=keyword) if keyword else q_filter
        
        # Exclude foods user ate recently (diversify menu)
        if user_context['recent_food_ids']:
            recent_ids = user_context['recent_food_ids'][-10:]
            q_filter &= ~Q(id__in=recent_ids)
        
        return q_filter
    
    @staticmethod
    def query_foods_from_db(user_context, request_type, meal_type='lunch', limit=20, exclude_food_ids=None):
        """
        Query DB để tìm foods phù hợp.
        
        Return: QuerySet of Foods
        """
        q_filter = MealPlanGeneratorService.build_food_filter(user_context, request_type)
        base_filter = Q(name__isnull=False)
        
        # Ưu tiên categories theo preference
        preferences = user_context['preferences']
        if preferences and preferences.preferred_categories:
            preferred_cats = preferences.preferred_categories
            if isinstance(preferred_cats, list) and preferred_cats:
                # Try to extract category IDs or names
                category_filter = Q()
                for cat in preferred_cats:
                    if isinstance(cat, dict) and 'id' in cat:
                        category_filter |= Q(category_id=cat['id'])
                    elif isinstance(cat, dict) and 'name' in cat:
                        category_filter |= Q(category__name=cat['name'])
                    elif isinstance(cat, str):
                        category_filter |= Q(category__name__icontains=cat)
                
                if category_filter:
                    q_filter |= category_filter
        
        if exclude_food_ids:
            q_filter &= ~Q(id__in=list(exclude_food_ids))

        # Query candidates trước, sau đó xếp theo chi phí nguyên liệu + độ đầy đủ dinh dưỡng.
        candidates = list(Food.objects.filter(q_filter).order_by('-created_at')[: max(limit * 3, limit)])
        budget_limit = None
        if user_context.get('profile_data'):
            budget_limit = user_context['profile_data'].get('budget_limit')

        scored = []
        for food in candidates:
            cost = MealPlanGeneratorService._estimate_food_cost(food)
            nutrition_score = MealPlanGeneratorService._nutrition_completeness_score(food)
            cost_value = cost if cost is not None else 10**12
            scored.append((cost_value, -nutrition_score, -int(food.id or 0), food))

        scored.sort()
        if budget_limit:
            affordable_foods = [
                food for cost_value, _, _, food in scored
                if cost_value == 10**12 or cost_value <= float(budget_limit)
            ]
            if not affordable_foods:
                return []
            candidate_foods = affordable_foods[: max(limit * 2, limit)]
        else:
            candidate_foods = [food for _, _, _, food in scored[: max(limit * 2, limit)]]

        account = user_context.get('account')
        if account and candidate_foods:
            ranked = rank_food_candidates(account, candidate_foods, limit=limit)
            if ranked:
                return [item['food'] for item in ranked]

        return candidate_foods[:limit]

    @staticmethod
    def _resolve_plan_days(request_text):
        text = (request_text or '').lower()
        if any(k in text for k in ['month', 'thang', 'tháng', '30 ngay', '30 ngày', 'cả tháng', 'ca thang']):
            return 30
        if any(k in text for k in ['week', 'tuan', 'tuần', '7 ngay', '7 ngày', 'cả tuần', 'ca tuan']):
            return 7

        match = re.search(r'(\d{1,2})\s*(ngay|ngày|day|days)', text)
        if match:
            return max(1, min(int(match.group(1)), 30))

        return 1

    @staticmethod
    def _resolve_plan_start_date(request_text):
        text = (request_text or '').lower()
        today = date.today()
        if 'ngay mai' in text or 'ngày mai' in text or 'tomorrow' in text:
            return today + timedelta(days=1)
        if 'tuan sau' in text or 'tuần sau' in text or 'next week' in text:
            return today + timedelta(days=7)
        return today

    @staticmethod
    def _estimate_food_cost(food):
        total_cost = Decimal('0')
        ingredients = FoodIngredient.objects.filter(food=food).select_related('ingredient')
        for food_ingredient in ingredients:
            price_obj = IngredientPrice.objects.filter(ingredient=food_ingredient.ingredient).first()
            if not price_obj:
                continue
            quantity_kg = (Decimal(str(food_ingredient.quantity_grams or 0)) / Decimal('1000'))
            if quantity_kg <= 0:
                continue
            total_cost += quantity_kg * Decimal(str(price_obj.price_per_unit))
        return float(total_cost) if total_cost > 0 else None

    @staticmethod
    def _nutrition_completeness_score(food):
        fields = [food.calories, food.protein, food.carbs, food.fat]
        return sum(1 for value in fields if float(value or 0) > 0)

    @staticmethod
    def _normalize_for_match(value):
        text = (value or '').strip().lower()
        if not text:
            return ''
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(char for char in text if not unicodedata.combining(char))
        text = re.sub(r'[^a-z0-9\s-]+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def _extract_budget_limit_from_text(request_text, user_context):
        profile_budget = user_context.get('profile_data', {}).get('budget_limit')
        if profile_budget:
            try:
                return float(profile_budget)
            except Exception:
                pass

        text = MealPlanGeneratorService._normalize_for_match(request_text)
        match = re.search(r'(\d+(?:[\.,]\d+)?)\s*(trieu|triệu|k|nghin|nghìn|d)', text)
        if not match:
            return None

        amount = match.group(1).replace(',', '.')
        try:
            value = float(amount)
        except Exception:
            return None

        unit = match.group(2)
        if unit in {'trieu', 'triệu'}:
            return value * 1_000_000
        if unit == 'k':
            return value * 1_000
        if unit in {'nghin', 'nghìn'}:
            return value * 1_000
        return value

    @staticmethod
    def _ingredient_price_value(ingredient):
        price_obj = IngredientPrice.objects.filter(ingredient=ingredient).order_by('-updated_at').first()
        if not price_obj:
            return None
        try:
            return float(price_obj.price_per_unit)
        except Exception:
            return None

    @staticmethod
    def _ingredient_nutrition_profile(ingredient):
        nutrition_obj = getattr(ingredient, 'nutrition', None)
        if not nutrition_obj:
            nutrition_obj = IngredientNutrition.objects.filter(ingredient=ingredient).first()

        if not nutrition_obj:
            return {
                'calories': None,
                'protein': None,
                'carbs': None,
                'fat': None,
                'fiber': None,
            }

        return {
            'calories': float(nutrition_obj.calories or 0),
            'protein': float(nutrition_obj.protein or 0),
            'carbs': float(nutrition_obj.carbs or 0),
            'fat': float(nutrition_obj.fat or 0),
            'fiber': float(nutrition_obj.fiber or 0),
        }

    @staticmethod
    def _ingredient_request_score(ingredient, request_text, user_context, meal_key='lunch'):
        request_blob = MealPlanGeneratorService._normalize_for_match(request_text)
        normalized_name = MealPlanGeneratorService._normalize_for_match(ingredient.name)
        request_tokens = set(request_blob.split())
        profile = user_context.get('profile_data') or {}
        health_goal = MealPlanGeneratorService._normalize_for_match(profile.get('health_goal') or '')
        medical_conditions = MealPlanGeneratorService._normalize_for_match(profile.get('medical_conditions') or '')
        dietary_preferences = MealPlanGeneratorService._normalize_for_match(profile.get('dietary_preferences') or '')
        combined_blob = ' '.join([request_blob, health_goal, medical_conditions, dietary_preferences]).strip()

        score = 0

        # Từ khóa trực tiếp
        if normalized_name in combined_blob or combined_blob in normalized_name:
            score += 8
        if any(token and (token in normalized_name or normalized_name in token) for token in request_tokens):
            score += 4

        # Ngữ cảnh ăn lành mạnh / bệnh lý / ăn kiêng
        health_keywords = {'lanh manh', 'lành mạnh', 'healthy', 'eat clean', 'eatclean', 'giam can', 'giảm cân', 'weight loss'}
        if any(keyword in combined_blob for keyword in health_keywords):
            nutrition = MealPlanGeneratorService._ingredient_nutrition_profile(ingredient)
            protein = nutrition.get('protein') or 0
            fiber = nutrition.get('fiber') or 0
            calories = nutrition.get('calories') or 0
            fat = nutrition.get('fat') or 0
            if protein > 0:
                score += min(4, int(protein / 5))
            if fiber > 0:
                score += min(3, int(fiber / 2))
            if calories and calories <= 250:
                score += 3
            if fat and fat <= 10:
                score += 2

        # Ưu tiên rẻ khi request có ngân sách
        budget_limit = MealPlanGeneratorService._extract_budget_limit_from_text(request_text, user_context)
        price_value = MealPlanGeneratorService._ingredient_price_value(ingredient)
        if budget_limit and price_value is not None:
            if price_value <= max(budget_limit / 20, 1_000):
                score += 8
            elif price_value <= max(budget_limit / 10, 2_000):
                score += 5
            elif price_value <= budget_limit:
                score += 2
            else:
                score -= 6

        # Meal type hints
        meal_hints = {
            'breakfast': ['trung', 'sua', 'sữa', 'yen mach', 'yến mạch', 'banh mi', 'bánh mì', 'chao', 'cháo'],
            'lunch': ['com', 'cơm', 'thit', 'thịt', 'ca', 'cá', 'rau', 'canh', 'xao', 'xào'],
            'dinner': ['rau', 'cá', 'thit', 'thịt', 'canh', 'luoc', 'luộc', 'hap', 'hấp'],
            'snack': ['trai cay', 'trái cây', 'sua chua', 'sữa chua', 'hat', 'hạt', 'banh', 'bánh'],
        }
        if any(hint in normalized_name for hint in meal_hints.get(meal_key, [])):
            score += 2

        # A little variety: avoid ingredients already used frequently recently if present in request context
        recent_ids = set(user_context.get('recent_food_ids', []))
        if recent_ids:
            score += 0

        return score

    @staticmethod
    def _ingredient_alias_table_exists():
        from django.db import connection

        try:
            return 'ingredient_aliases' in connection.introspection.table_names()
        except Exception:
            return False

    @staticmethod
    def _extract_candidate_ingredients_from_db(user_context, request_text, meal_key='lunch', limit=12):
        profile = user_context.get('profile_data') or {}
        request_blob = MealPlanGeneratorService._normalize_for_match(' '.join([
            request_text or '',
            profile.get('health_goal') or '',
            profile.get('medical_conditions') or '',
            profile.get('dietary_preferences') or '',
        ]))
        request_tokens = set(request_blob.split())

        meal_hints = {
            'breakfast': ['trung', 'trứng', 'sua', 'sữa', 'banh mi', 'bánh mì', 'yen mach', 'yến mạch', 'chao', 'cháo'],
            'lunch': ['com', 'cơm', 'thit', 'thịt', 'ca', 'cá', 'rau', 'canh', 'xao', 'xào'],
            'dinner': ['rau', 'cá', 'thit', 'thịt', 'canh', 'luoc', 'luộc', 'hap', 'hấp'],
            'snack': ['trai cay', 'trái cây', 'sua chua', 'sữa chua', 'hat', 'hạt', 'banh', 'bánh'],
        }
        hint_tokens = set(meal_hints.get(meal_key, []))

        ingredients_qs = Ingredient.objects.filter(is_deleted=False).order_by('name')
        if MealPlanGeneratorService._ingredient_alias_table_exists():
            ingredients_qs = ingredients_qs.prefetch_related('aliases')
        ingredients = list(ingredients_qs)

        scored = []
        for ingredient in ingredients:
            normalized_name = MealPlanGeneratorService._normalize_for_match(ingredient.name)
            if not normalized_name:
                continue

            score = MealPlanGeneratorService._ingredient_request_score(ingredient, request_text, user_context, meal_key=meal_key)

            if any(hint and hint in normalized_name for hint in hint_tokens):
                score += 1

            if MealPlanGeneratorService._ingredient_alias_table_exists():
                try:
                    aliases = [MealPlanGeneratorService._normalize_for_match(alias.alias) for alias in ingredient.aliases.all()]
                    if any(alias and (alias in request_blob or request_blob in alias) for alias in aliases):
                        score += 4
                except Exception:
                    pass

            if score > 0:
                scored.append((score, normalized_name, ingredient))

        scored.sort(key=lambda item: (-item[0], item[1]))
        selected = [ingredient for _, _, ingredient in scored[:limit]]

        if not selected:
            fallback_names = [
                'trứng', 'cơm', 'thịt gà', 'thịt heo', 'thịt bò', 'cá', 'tôm',
                'rau', 'cà chua', 'hành', 'tỏi', 'nấm', 'đậu hũ', 'sữa', 'phô mai',
                'khoai tây', 'khoai lang', 'xà lách', 'dưa chuột', 'cà rốt', 'bánh mì',
            ]
            name_map = {MealPlanGeneratorService._normalize_for_match(item.name): item for item in ingredients}
            for fallback_name in fallback_names:
                ingredient = name_map.get(MealPlanGeneratorService._normalize_for_match(fallback_name))
                if ingredient and ingredient not in selected:
                    selected.append(ingredient)
                if len(selected) >= limit:
                    break

        if not selected:
            selected = ingredients[:limit]

        return selected[:limit]

    @staticmethod
    def _parse_recipe_payload_from_gemini(response_text):
        if not response_text:
            return None

        cleaned = re.sub(r'```(?:json)?', '', response_text, flags=re.IGNORECASE).strip()
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if not json_match:
            return None

        try:
            payload = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            return None

        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _quantity_to_grams(quantity, unit):
        try:
            qty = Decimal(str(quantity or 0))
        except Exception:
            qty = Decimal('0')

        unit_text = MealPlanGeneratorService._normalize_for_match(unit or 'g')
        if unit_text in {'g', 'gram', 'grams', 'gr'}:
            return qty
        if unit_text in {'kg', 'kilogram', 'kilograms'}:
            return qty * Decimal('1000')
        if unit_text in {'mg'}:
            return qty / Decimal('1000')
        if unit_text in {'ml', 'milliliter', 'milliliters'}:
            return qty
        if unit_text in {'l', 'liter', 'litre', 'liters', 'litres'}:
            return qty * Decimal('1000')
        if unit_text in {'cai', 'cái', 'qua', 'quả', 'mieng', 'miếng', 'trai', 'trái', 'bat', 'bát', 'chen', 'chén', 'muong', 'muỗng', 'thia', 'thìa'}:
            return qty * Decimal('50')
        return qty * Decimal('100')

    @staticmethod
    def _safe_gemini_generate_text(prompt, system_instruction=None, max_output_tokens=2048):
        try:
            return _gemini_generate_text(
                prompt,
                system_instruction=system_instruction,
                max_output_tokens=max_output_tokens,
            )
        except Exception:
            return None

    @staticmethod
    def _generate_food_from_ingredients_with_gemini(account, request_text, user_context, analyzed_request, meal_key, target_date=None):
        if not AI_AVAILABLE:
            return None

        candidate_ingredients = MealPlanGeneratorService._extract_candidate_ingredients_from_db(
            user_context,
            request_text,
            meal_key=meal_key,
            limit=12,
        )
        ingredient_names = [ingredient.name for ingredient in candidate_ingredients if ingredient and ingredient.name]

        meal_label, min_cal, max_cal = MealPlanGeneratorService.MEAL_TYPES.get(meal_key, ('Món ăn', 300, 600))
        profile = user_context.get('profile_data') or {}
        diseases = ', '.join(user_context.get('diseases') or []) or 'không có'
        dietary = profile.get('dietary_preferences') or 'không có'
        health_goal = profile.get('health_goal') or 'chưa cung cấp'

        ingredient_context = (
            f'Nguyên liệu có sẵn trong CSDL, ưu tiên dùng đúng các nguyên liệu này: {", ".join(ingredient_names)}\n\n'
            if ingredient_names
            else 'Hiện không có đủ nguyên liệu gợi ý trong CSDL. Hãy tự đề xuất 1 món mới phù hợp mục tiêu và trả về JSON đầy đủ để hệ thống lưu món vào CSDL.\n\n'
        )

        prompt = (
            f'Bạn là đầu bếp chuyên nghiệp và chuyên gia dinh dưỡng.\n'
            f'Hãy tạo 1 món ăn phù hợp cho {meal_label} ({int(min_cal)}-{int(max_cal)} kcal).\n'
            f'Yêu cầu của người dùng: {request_text}\n'
            f'Mục tiêu sức khỏe: {health_goal}\n'
            f'Bệnh nền: {diseases}\n'
            f'Sở thích ăn: {dietary}\n'
            f'{ingredient_context}'
            'Chỉ trả về JSON với cấu trúc sau:\n'
            '{\n'
            '  "name": "Tên món",\n'
            '  "summary": "Mô tả ngắn",\n'
            '  "category": "Mon chinh",\n'
            '  "ingredients": [\n'
            '    {"name": "trứng", "quantity": 2, "unit": "cái"}\n'
            '  ],\n'
            '  "instructions": ["Bước 1", "Bước 2"],\n'
            '  "nutrition": {"calories": 300, "protein": 15, "carbs": 20, "fat": 10, "fiber": 3},\n'
            '  "confidence": 0.85\n'
            '}'
        )

        system_instruction = (
            'Bạn là trợ lý tạo món ăn cho Smart Home Chef. '
            'Nếu có danh sách nguyên liệu thì ưu tiên dùng các nguyên liệu đó. '
            'Nếu không có nguyên liệu, hãy tự tạo món phù hợp mục tiêu dinh dưỡng của người dùng. '
            'Trả về JSON hợp lệ, không thêm giải thích ngoài JSON.'
        )

        response_text = MealPlanGeneratorService._safe_gemini_generate_text(
            prompt,
            system_instruction=system_instruction,
            max_output_tokens=2048,
        )

        recipe_payload = MealPlanGeneratorService._parse_recipe_payload_from_gemini(response_text)
        if not recipe_payload:
            return None

        food_name = str(recipe_payload.get('name') or '').strip()
        if not food_name:
            return None

        category_name = str(recipe_payload.get('category') or meal_label or 'AI Generated').strip() or 'AI Generated'
        summary = str(recipe_payload.get('summary') or '').strip()
        instructions = recipe_payload.get('instructions') or []
        if isinstance(instructions, list):
            instructions_text = '\n'.join(
                f'{idx + 1}. {str(step).strip()}'
                for idx, step in enumerate(instructions)
                if str(step).strip()
            )
        else:
            instructions_text = str(instructions).strip()

        nutrition = recipe_payload.get('nutrition') or {}
        ingredients_payload = recipe_payload.get('ingredients') or []
        if not isinstance(ingredients_payload, list):
            ingredients_payload = []

        with transaction.atomic():
            existing_food = Food.objects.filter(name__iexact=food_name).first()
            if existing_food:
                return existing_food

            category_obj, _ = FoodCategory.objects.get_or_create(name=category_name)
            food = Food.objects.create(
                name=food_name,
                normalized_name=MealPlanGeneratorService._normalize_for_match(food_name),
                category=category_obj,
                calories=Decimal(str(nutrition.get('calories', 0) or 0)),
                protein=Decimal(str(nutrition.get('protein', 0) or 0)),
                carbs=Decimal(str(nutrition.get('carbs', 0) or 0)),
                fat=Decimal(str(nutrition.get('fat', 0) or 0)),
                fiber=Decimal(str(nutrition.get('fiber', 0) or 0)),
                is_vegetarian=bool(recipe_payload.get('is_vegetarian', False)),
                is_diabetes_friendly=bool(recipe_payload.get('is_diabetes_friendly', analyzed_request.get('type') == 'health')),
                is_weight_loss_friendly=bool(recipe_payload.get('is_weight_loss_friendly', analyzed_request.get('type') in {'health', 'budget'})),
                description=' | '.join(part for part in [summary, f'AI-generated from ingredients for {meal_label}', f'Request: {request_text}'] if part),
            )

            saved_ingredients = 0
            for ingredient_item in ingredients_payload:
                if not isinstance(ingredient_item, dict):
                    continue

                raw_name = str(ingredient_item.get('name') or '').strip()
                if not raw_name:
                    continue

                ingredient = Ingredient.objects.filter(name__iexact=raw_name, is_deleted=False).first()
                if not ingredient and MealPlanGeneratorService._ingredient_alias_table_exists():
                    alias_row = IngredientAlias.objects.filter(alias__iexact=raw_name).select_related('ingredient').first()
                    if alias_row and alias_row.ingredient:
                        ingredient = alias_row.ingredient
                if not ingredient:
                    ingredient = Ingredient.objects.filter(name__icontains=raw_name, is_deleted=False).order_by('name').first()
                if not ingredient:
                    ingredient = get_or_fetch_ingredient(raw_name)
                if not ingredient:
                    continue

                quantity_grams = MealPlanGeneratorService._quantity_to_grams(
                    ingredient_item.get('quantity', 0),
                    ingredient_item.get('unit', 'g'),
                )
                FoodIngredient.objects.update_or_create(
                    food=food,
                    ingredient=ingredient,
                    defaults={'quantity_grams': quantity_grams},
                )
                saved_ingredients += 1

            if saved_ingredients == 0:
                # Vẫn giữ món AI tạo để lấp meal plan khi DB nghèo dữ liệu nguyên liệu.
                food.description = ' | '.join(
                    part for part in [
                        str(food.description or '').strip(),
                        'AI-generated: ingredient links unavailable'
                    ]
                    if part
                )
                food.save(update_fields=['description'])

            return food
    
    @staticmethod
    def get_foods_for_meal_plan(user_context, request_type, target_date=None):
        """
        Lập danh sách foods cho toàn bộ meal plan (breakfast, lunch, dinner, snack).
        Nếu DB không đủ → cần call API (Gemini fallback).
        
        Return: dict {
            'breakfast': [Food...],
            'lunch': [Food...],
            'dinner': [Food...],
            'snack': [Food...],
            'api_used': bool,
            'api_needed': bool,
        }
        """
        result = {
            'breakfast': [],
            'lunch': [],
            'dinner': [],
            'snack': [],
            'api_used': False,
            'api_needed': False,
        }
        
        # Lấy foods từ DB cho mỗi meal type
        for meal_key in ['breakfast', 'lunch', 'dinner', 'snack']:
            foods = MealPlanGeneratorService.query_foods_from_db(
                user_context, request_type, meal_type=meal_key, limit=5
            )
            result[meal_key] = list(foods)
        
        # Kiểm tra nếu không đủ foods
        filled_meals = sum(1 for v in result.values() if isinstance(v, list) and len(v) >= 1)
        if filled_meals < 3:
            result['api_needed'] = True
        
        return result
    
    @staticmethod
    def generate_meal_plan_with_gemini(account, request_text, user_context, analyzed_request, target_date=None):
        """
        Fallback method: Dùng Gemini API để tạo thực đơn khi DB không đủ foods.
        
        Thực hiện các bước tương tự generate_meal_plan() nhưng qua Gemini:
        1. analyze_request() - đã làm
        2. get_user_context() - đã làm
        3. build_food_filter() - dùng Gemini để recommend
        4. query_foods_from_db() - truy vấn foods từ Gemini recommendations
        5. generate_meal_plan() - tạo MealPlan từ kết quả Gemini
        
        Return: dict {
            'success': bool,
            'meal_plans': [MealPlan...],
            'message': str,
            'api_used': True,
            'recommendations': {...}
        }
        """
        if not AI_AVAILABLE:
            return {
                'success': False,
                'meal_plans': [],
                'message': 'Gemini API không khả dụng. Vui lòng thử lại sau.',
                'api_used': False,
            }
        
        if not target_date:
            target_date = date.today()
        
        try:
            # Chuẩn bị prompt cho Gemini
            profile = user_context.get('profile_data', {})
            diseases = user_context.get('diseases', [])
            preferences = user_context.get('preferences')
            
            system_instruction = (
                'Bạn là chuyên gia dinh dưỡng của Smart Home Chef. '
                'Hãy gợi ý các món ăn phù hợp dựa trên hồ sơ và yêu cầu của người dùng. '
                'Trả lời bằng tiếng Việt và cung cấp JSON với danh sách các món cho mỗi bữa.'
            )
            
            disease_str = ', '.join(diseases) if diseases else 'không có'
            goal_str = profile.get('health_goal', 'tăng cường sức khỏe chung')
            budget_str = f"{profile.get('budget_limit', 'không giới hạn')}"
            dietary = profile.get('dietary_preferences', 'không có')
            
            prompt = (
                f'Hôm nay ({target_date.strftime("%d/%m/%Y")}), hãy lập thực đơn cho:\n'
                f'- Bệnh lý: {disease_str}\n'
                f'- Mục tiêu: {goal_str}\n'
                f'- Ngân sách: {budget_str} VNĐ/ngày\n'
                f'- Sở thích ăn: {dietary}\n'
                f'- Yêu cầu: {request_text}\n\n'
                f'Gợi ý 4-5 món cho mỗi bữa (sáng, trưa, tối, phụ) dưới dạng JSON:\n'
                '{"breakfast": ["tên món 1", "tên món 2"], '
                '"lunch": ["tên món 1", "tên món 2"], '
                '"dinner": ["tên món 1", "tên món 2"], '
                '"snack": ["tên món 1"]}'
            )
            
            # Gọi Gemini để lấy gợi ý
            gemini_response = MealPlanGeneratorService._safe_gemini_generate_text(
                prompt,
                system_instruction=system_instruction,
                max_output_tokens=1024,
            )
            
            # Parse JSON response
            recommendations = {}
            if gemini_response:
                # Cố gắng extract JSON từ response
                import re
                json_match = re.search(r'\{[^{}]*(?:"(?:breakfast|lunch|dinner|snack)"[^}]*)*\}', gemini_response, re.DOTALL)
                if json_match:
                    try:
                        recommendations = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        # Fallback: parse thủ công từ response text
                        recommendations = _parse_gemini_meal_recommendations(gemini_response)
            
            if not recommendations:
                return {
                    'success': False,
                    'meal_plans': [],
                    'message': 'Không thể parse gợi ý từ Gemini. Vui lòng thử lại.',
                    'api_used': True,
                }
            
            # Bước 4: Query foods từ DB dựa trên gợi ý Gemini
            meal_plans = []
            meal_order = ['breakfast', 'lunch', 'dinner', 'snack']
            
            for meal_key in meal_order:
                suggestions = recommendations.get(meal_key, [])
                if not suggestions:
                    continue
                
                # Tìm food từ DB match với suggestion
                selected_food = None
                for suggestion in suggestions:
                    # Search by name match
                    food_match = Food.objects.filter(
                        name__icontains=suggestion
                    ).exclude(id__in=user_context.get('recent_food_ids', [])).first()
                    
                    if not food_match:
                        # Thử tìm partial match
                        words = suggestion.split()
                        for word in words:
                            if len(word) > 3:
                                food_match = Food.objects.filter(
                                    name__icontains=word
                                ).exclude(id__in=user_context.get('recent_food_ids', [])).first()
                                if food_match:
                                    break
                    
                    if food_match:
                        selected_food = food_match
                        break
                
                # Nếu không tìm được, lấy food random phù hợp từ DB
                if not selected_food:
                    q_filter = MealPlanGeneratorService.build_food_filter(user_context, analyzed_request['type'])
                    selected_food = Food.objects.filter(q_filter).exclude(
                        id__in=user_context.get('recent_food_ids', [])
                    ).first()

                if not selected_food:
                    selected_food = MealPlanGeneratorService._generate_food_from_ingredients_with_gemini(
                        account=account,
                        request_text=request_text,
                        user_context=user_context,
                        analyzed_request=analyzed_request,
                        meal_key=meal_key,
                        target_date=target_date,
                    )
                
                if not selected_food:
                    continue
                
                # Tính servings
                meal_vi, min_cal, max_cal = MealPlanGeneratorService.MEAL_TYPES[meal_key]
                servings = 1.0
                food_cal = float(selected_food.calories or 0)
                if food_cal > 0:
                    target_cal = (max_cal + min_cal) / 2
                    servings = target_cal / food_cal
                    servings = round(servings, 2)
                
                # Tạo MealPlan
                plan = MealPlan.objects.create(
                    account=account,
                    food=selected_food,
                    date=target_date,
                    meal_type=meal_vi,
                    servings=Decimal(str(servings)),
                    notes=f'AI-generated with Gemini fallback ({analyzed_request["type"]} plan): {request_text}'
                )
                meal_plans.append(plan)
            
            if not meal_plans:
                return {
                    'success': False,
                    'meal_plans': [],
                    'message': 'Không tìm thấy foods phù hợp trong database để match với gợi ý Gemini.',
                    'api_used': True,
                    'recommendations': recommendations,
                }
            
            return {
                'success': True,
                'meal_plans': meal_plans,
                'message': f'Tạo thực đơn thành công (Gemini fallback) cho {target_date} dựa trên yêu cầu: {request_text}',
                'api_used': True,
                'recommendations': recommendations,
            }
        
        except Exception as e:
            return {
                'success': False,
                'meal_plans': [],
                'message': f'Lỗi gọi Gemini API: {str(e)}',
                'api_used': True,
            }
    
    @staticmethod
    def _parse_gemini_meal_recommendations(text):
        """Parse gợi ý món ăn từ response text của Gemini (fallback parser)."""
        recommendations = {'breakfast': [], 'lunch': [], 'dinner': [], 'snack': []}
        
        # Tìm sections cho mỗi bữa
        for meal_key in recommendations.keys():
            # Các keyword để nhận diện bữa ăn
            meal_keywords = {
                'breakfast': ['sáng', 'breakfast', 'bữa sáng'],
                'lunch': ['trưa', 'lunch', 'bữa trưa', 'cơm'],
                'dinner': ['tối', 'dinner', 'bữa tối'],
                'snack': ['phụ', 'snack', 'xen', 'ăn vặt'],
            }
            
            text_lower = text.lower()
            section_start = -1
            
            # Tìm vị trí bắt đầu của section
            for keyword in meal_keywords[meal_key]:
                idx = text_lower.find(keyword)
                if idx != -1:
                    section_start = idx
                    break
            
            if section_start == -1:
                continue
            
            # Lấy text của section (đến section tiếp theo hoặc hết)
            section_text = text[section_start:]
            next_section_idx = float('inf')
            for other_meal in recommendations.keys():
                if other_meal == meal_key:
                    continue
                for keyword in meal_keywords[other_meal]:
                    idx = section_text.lower().find(keyword, 10)  # Skip first 10 chars
                    if idx != -1:
                        next_section_idx = min(next_section_idx, idx)
            
            if next_section_idx < float('inf'):
                section_text = section_text[:next_section_idx]
            
            # Extract items từ section (phân tách bằng - hoặc numbers)
            lines = section_text.split('\n')[1:]  # Skip header
            items = []
            for line in lines:
                line = line.strip()
                if line and len(line) > 2:
                    # Remove leading bullet, number, dash
                    line = re.sub(r'^[-•*\d.)\s]+', '', line).strip()
                    if line and len(line) > 2:
                        items.append(line)
                if len(items) >= 5:  # Max 5 items per meal
                    break
            
            recommendations[meal_key] = items
        
        return recommendations
    
    @staticmethod
    def generate_meal_plan(account, request_text, target_date=None):
        """
        Luồng chính: tạo meal plan từ request của user.
        
        Return: {
            'success': bool,
            'meal_plans': [MealPlan...],
            'message': str,
            'api_fallback_used': bool,
            'request_type': str,
        }
        """
        if not target_date:
            target_date = MealPlanGeneratorService._resolve_plan_start_date(request_text)
        
        try:
            # Bước 1: Phân tích request
            analyzed = MealPlanGeneratorService.analyze_request(request_text)
            
            # Bước 2: Lấy context user
            user_context = MealPlanGeneratorService.get_user_context(account)

            plan_days = MealPlanGeneratorService._resolve_plan_days(request_text)
            
            meal_plans = []
            used_food_ids = set(user_context.get('recent_food_ids', []))
            meal_order = ['breakfast', 'lunch', 'dinner', 'snack']
            api_fallback_used = False

            # Bước 3-4: Lập meal plan cho từng ngày, ưu tiên món có giá/chi phí hợp lý
            for day_index in range(plan_days):
                current_date = target_date + timedelta(days=day_index)
                day_created = False
            
                for meal_key in meal_order:
                    foods = MealPlanGeneratorService.query_foods_from_db(
                        user_context,
                        analyzed['type'],
                        meal_type=meal_key,
                        limit=10,
                        exclude_food_ids=used_food_ids,
                    )
                    if not foods:
                        generated_food = MealPlanGeneratorService._generate_food_from_ingredients_with_gemini(
                            account=account,
                            request_text=request_text,
                            user_context=user_context,
                            analyzed_request=analyzed,
                            meal_key=meal_key,
                            target_date=current_date,
                        )
                        if generated_food:
                            foods = [generated_food]
                            api_fallback_used = True
                        else:
                            continue

                    selected_food = foods[0]
                    if float(selected_food.calories or 0) <= 0 or float(selected_food.protein or 0) <= 0:
                        NutritionDataFiller.fill_missing_nutrition(
                            selected_food,
                            use_spoonacular=True,
                            use_gemini=True,
                        )
                        selected_food.refresh_from_db()

                    meal_vi, min_cal, max_cal = MealPlanGeneratorService.MEAL_TYPES[meal_key]

                    # Tính servings sao cho calories vừa target
                    servings = 1.0
                    food_cal = float(selected_food.calories or 0)
                    if food_cal > 0:
                        target_cal = (max_cal + min_cal) / 2
                        servings = target_cal / food_cal
                        servings = round(servings, 2)

                    MealPlan.objects.filter(
                        account=account,
                        date=current_date,
                        meal_type=meal_vi,
                    ).delete()

                    plan = MealPlan.objects.create(
                        account=account,
                        food=selected_food,
                        date=current_date,
                        meal_type=meal_vi,
                        servings=Decimal(str(servings)),
                        notes=f'[AUTO_PLAN] AI-generated ({analyzed["type"]} plan): {request_text}'
                    )
                    meal_plans.append(plan)
                    used_food_ids.add(selected_food.id)
                    day_created = True

                if not day_created and plan_days == 1 and AI_AVAILABLE:
                    gemini_result = MealPlanGeneratorService.generate_meal_plan_with_gemini(
                        account, request_text, user_context, analyzed, current_date
                    )
                    api_fallback_used = True
                    return gemini_result
            
            if not meal_plans:
                fallback_meal_plans = []
                for day_index in range(plan_days):
                    current_date = target_date + timedelta(days=day_index)
                    for meal_key in meal_order:
                        generated_food = MealPlanGeneratorService._generate_food_from_ingredients_with_gemini(
                            account=account,
                            request_text=request_text,
                            user_context=user_context,
                            analyzed_request=analyzed,
                            meal_key=meal_key,
                            target_date=current_date,
                        )
                        if not generated_food:
                            continue

                        meal_vi, min_cal, max_cal = MealPlanGeneratorService.MEAL_TYPES[meal_key]
                        servings = 1.0
                        food_cal = float(generated_food.calories or 0)
                        if food_cal > 0:
                            target_cal = (max_cal + min_cal) / 2
                            servings = round(target_cal / food_cal, 2)

                        MealPlan.objects.filter(
                            account=account,
                            date=current_date,
                            meal_type=meal_vi,
                        ).delete()

                        plan = MealPlan.objects.create(
                            account=account,
                            food=generated_food,
                            date=current_date,
                            meal_type=meal_vi,
                            servings=Decimal(str(servings)),
                            notes=f'[AUTO_PLAN] Gemini ingredient fallback ({analyzed["type"]} plan): {request_text}'
                        )
                        fallback_meal_plans.append(plan)
                        api_fallback_used = True

                if fallback_meal_plans:
                    date_labels = sorted({str(plan.date) for plan in fallback_meal_plans})
                    return {
                        'success': True,
                        'meal_plans': fallback_meal_plans,
                        'message': (
                            f'Gemini đã tự tạo món từ nguyên liệu phù hợp và lập thực đơn cho {plan_days} ngày từ {target_date}. '
                            f'Đã lưu vào trang Thực đơn.'
                        ),
                        'api_fallback_used': True,
                        'request_type': analyzed['type'],
                        'plan_days': plan_days,
                        'plan_dates': date_labels,
                    }

                return {
                    'success': False,
                    'meal_plans': [],
                    'message': 'Không tìm được nguyên liệu phù hợp để Gemini tạo món thay thế. Vui lòng bổ sung dữ liệu hoặc thử lại.',
                    'api_fallback_used': api_fallback_used,
                    'request_type': analyzed['type'],
                    'plan_days': plan_days,
                }
            
            date_labels = sorted({str(plan.date) for plan in meal_plans})
            created_days = len(date_labels)
            return {
                'success': True,
                'meal_plans': meal_plans,
                'message': (
                    f'Tạo thực đơn thành công cho {created_days}/{plan_days} ngày từ {target_date} dựa trên yêu cầu: {request_text}. '
                    f'Đã lưu vào trang Thực đơn.'
                ),
                'api_fallback_used': api_fallback_used,
                'request_type': analyzed['type'],
                'plan_days': plan_days,
                'plan_dates': date_labels,
            }
        
        except Exception as e:
            return {
                'success': False,
                'meal_plans': [],
                'message': f'Lỗi tạo meal plan: {str(e)}',
                'api_fallback_used': False,
                'request_type': 'error',
                'plan_days': 0,
            }
