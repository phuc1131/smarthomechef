"""
Module tạo công thức nấu ăn từ danh sách nguyên liệu.

Mục đích:
- Gọi Gemini API để tạo công thức từ danh sách nguyên liệu
- Trả về danh sách món ăn có thể làm (sorted by complexity & confidence)
- Generate chi tiết công thức (instructions, time, tips, etc.)

GHI NHỚ QUAN TRỌNG:
- Luôn validate độ hợp lý của kết hợp nguyên liệu (tránh món bất hợp lý)
- Nếu thiếu nguyên liệu chính → suggest thay thế hoặc bỏ qua
- Cache kết quả để tránh gọi API lặp lại cùng danh sách nguyên liệu
- Confidence score cho mỗi công thức (0-1)
"""

import json
import re
from django.db.models import Count, Q
from app.config import GEMINI_API_KEY, GEMINI_MODEL
from apps.nutrition.models import Food, FoodIngredient
from app.services.external_apis import _gemini_generate_text
from app.services.ingredient_parser_service import _normalize_ingredient_name
from app.services.personalization_service import rank_food_candidates

# Các thành phần bất hợp lý (tránh kết hợp)
INCOMPATIBILITY_MATRIX = {
    'sữa': {'cá', 'tôm', 'cua', 'hải sản', 'dâu'},
    'phô mai': {'cá', 'tôm', 'cua', 'hải sản'},
    'dưa hấu': {'sữa'},
    'nước ép trái cây': {'sữa'},
    'cá': {'sữa', 'phô mai', 'dầu dừa'},
    'tôm': {'sữa', 'phô mai'},
    'cua': {'sữa', 'phô mai'},
}

# Điểm độ phức tạp của các nguyên liệu
INGREDIENT_COMPLEXITY = {
    'trứng': 1,
    'bánh mì': 1,
    'cơm': 1,
    'gạo': 1,
    'nước': 1,
    'muối': 1,
    'đường': 1,
    'dầu ăn': 1,
    'tỏi': 2,
    'hành': 2,
    'cà chua': 2,
    'rau': 2,
    'thịt heo': 2,
    'thịt gà': 2,
    'cá': 3,
    'tôm': 3,
    'mì ý': 3,
    'phô mai': 3,
}


def _check_ingredient_compatibility(ingredients):
    """
    Kiểm tra xem danh sách nguyên liệu có kết hợp hợp lý không.
    
    Return:
    - (is_compatible: bool, warning_message: str)
    """
    ingredients_text = ' '.join([ing.lower() for ing in ingredients])
    for item, disallowed in INCOMPATIBILITY_MATRIX.items():
        if item in ingredients_text:
            for blocked in disallowed:
                if blocked in ingredients_text:
                    return False, f"Kết hợp '{item}' + '{blocked}' có thể không hợp lý."    
    return True, ""


def _calculate_recipe_complexity(ingredients):
    """Tính độ phức tạp của công thức dựa trên nguyên liệu."""
    total_complexity = 0
    for ing in ingredients:
        ing_lower = ing.lower()
        for keyword, complexity in INGREDIENT_COMPLEXITY.items():
            if keyword in ing_lower:
                total_complexity += complexity
                break
        else:
            total_complexity += 2  # Default
    
    avg_complexity = total_complexity / len(ingredients) if ingredients else 0
    
    if avg_complexity < 1.5:
        return 'easy', 0.9
    elif avg_complexity < 2.5:
        return 'medium', 0.7
    else:
        return 'hard', 0.5


def _ingredient_matches(ingredient_name, normalized_keywords):
    lower_name = ingredient_name.lower()
    for keyword in normalized_keywords:
        if keyword in lower_name or lower_name in keyword:
            return True
    return False


def _normalize_ingredient_keywords(ingredients):
    normalized = []
    for ing in ingredients:
        if not ing:
            continue
        keyword = _normalize_ingredient_name(ing).strip().lower()
        if keyword and keyword not in normalized:
            normalized.append(keyword)
    return normalized


def _build_recipe_from_food(food, available_keywords):
    food_ingredients = list(food.foodingredient_set.select_related('ingredient').all())
    required = [fi.ingredient.name for fi in food_ingredients if fi.ingredient and fi.ingredient.name]
    matched = [req for req in required if _ingredient_matches(req, available_keywords)]
    missing = [req for req in required if req not in matched]
    total_required = len(required) or 1
    match_ratio = len(matched) / total_required
    difficulty, _ = _calculate_recipe_complexity(required)
    confidence = 0.95 if not missing else round(max(0.55, 0.5 + (match_ratio * 0.4)), 2)

    return {
        'name': food.name,
        'time': getattr(food, 'serving_size', None) or '30 phút',
        'difficulty': difficulty,
        'confidence': confidence,
        'missing_ingredients': missing,
        'substitute_suggestions': {req: [] for req in missing} if missing else {},
    }


def _find_recipes_from_db(ingredients, limit=10):
    keywords = _normalize_ingredient_keywords(ingredients)
    if not keywords:
        return []

    query = Q()
    for keyword in keywords:
        query |= Q(foodingredient__ingredient__name__icontains=keyword)

    foods = (
        Food.objects.filter(query)
        .distinct()
        .prefetch_related('foodingredient_set__ingredient')
    )

    recipes = []
    for food in foods:
        recipe = _build_recipe_from_food(food, keywords)
        recipes.append(recipe)

    recipes = sorted(
        recipes,
        key=lambda r: (
            len(r['missing_ingredients']),
            r['difficulty'] != 'easy',
            -r['confidence']
        )
    )
    return recipes[:limit]


def recommend_recipes_from_ingredients(ingredients, limit=10, account=None):
    """
    Gợi ý danh sách món ăn có thể làm từ nguyên liệu.
    
    Tham số:
    - ingredients: [str] - danh sách nguyên liệu chuẩn hóa
    - limit: int - số lượng gợi ý tối đa
    
    Trả về:
    - {
        'success': bool,
        'recipes': [
            {
                'name': str,  # Tên món ăn
                'time': str,  # Thời gian nấu (VD: "20 phút")
                'difficulty': str,  # 'easy', 'medium', 'hard'
                'confidence': float,  # 0-1
                'missing_ingredients': [str],  # Nguyên liệu có thể thiếu
                'substitute_suggestions': {ing: [substitutes]},  # Gợi ý thay thế
            }
        ],
        'message': str,
      }
    """
    if not ingredients:
        return {
            'success': False,
            'recipes': [],
            'message': 'Danh sách nguyên liệu trống',
        }

    # Check compatibility
    is_compatible, warning = _check_ingredient_compatibility(ingredients)

    db_recipes = _find_recipes_from_db(ingredients, limit)
    if db_recipes:
        if account:
            food_lookup = {
                recipe['name']: Food.objects.filter(name__iexact=recipe['name']).first()
                for recipe in db_recipes
            }
            ranked_foods = [food for food in food_lookup.values() if food]
            if ranked_foods:
                ranked_payload = rank_food_candidates(account, ranked_foods, limit=len(ranked_foods))
                rank_map = {item['food'].id: idx for idx, item in enumerate(ranked_payload)}
                db_recipes = sorted(
                    db_recipes,
                    key=lambda recipe: rank_map.get(
                        (food_lookup.get(recipe['name']).id if food_lookup.get(recipe['name']) else None),
                        10**6,
                    ),
                )

        response = {
            'success': True,
            'recipes': db_recipes,
            'message': f'Found {len(db_recipes)} recipes from local database',
        }
        if not is_compatible:
            response['warning'] = warning
        return response

    # Nếu không tìm được trong DB thì mới dùng Gemini
    try:
        recipes = _get_recipes_from_gemini(ingredients, limit)
        if recipes:
            recipes = sorted(
                recipes,
                key=lambda r: (r.get('difficulty') != 'easy', -r.get('confidence', 0.5))
            )
            response = {
                'success': True,
                'recipes': recipes[:limit],
                'message': f'Found {len(recipes)} recipes from Gemini',
            }
            if not is_compatible:
                response['warning'] = warning
            return response
    except Exception:
        pass

    # Fallback: từ danh sách hardcoded
    fallback_recipes = _get_fallback_recipes(ingredients, limit)
    response = {
        'success': len(fallback_recipes) > 0,
        'recipes': fallback_recipes,
        'message': f'Found {len(fallback_recipes)} recipes (fallback)',
    }
    if not is_compatible:
        response['warning'] = warning
    return response


def _get_recipes_from_gemini(ingredients, limit=10):
    """Gọi Gemini API để lấy danh sách công thức từ nguyên liệu."""
    try:
        ingredients_str = ', '.join(ingredients)
        prompt = f"""Bạn là đầu bếp chuyên nghiệp người Việt.

Người dùng có những nguyên liệu sau: {ingredients_str}

Hãy gợi ý {min(limit, 5)} món ăn Việt Nam hoặc quốc tế có thể làm từ những nguyên liệu này.

Yêu cầu:
1. Trả về JSON array
2. Mỗi item có: name, time_minutes (số phút), difficulty (easy/medium/hard), confidence (0-1)
3. Sắp xếp theo dễ làm trước, sau đó theo confidence cao trước
4. Chỉ trả về JSON, không có text khác

Ví dụ output:
[
  {{"name": "Trứng chiên hành", "time_minutes": 10, "difficulty": "easy", "confidence": 0.95}},
  {{"name": "Cơm trứng thịt heo", "time_minutes": 15, "difficulty": "easy", "confidence": 0.9}}
]

Hãy gợi ý công thức:"""

        response_text = _gemini_generate_text(prompt, max_output_tokens=1024)
        if not response_text:
            return []
        
        # Parse JSON từ response
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if not json_match:
            return []
        
        json_str = json_match.group(0)
        recipes = json.loads(json_str)
        
        # Validate và format
        result = []
        for recipe in recipes:
            if isinstance(recipe, dict) and 'name' in recipe:
                result.append({
                    'name': recipe.get('name', '').strip(),
                    'time': f"{recipe.get('time_minutes', 0)} phút",
                    'difficulty': recipe.get('difficulty', 'medium').lower(),
                    'confidence': float(recipe.get('confidence', 0.7)),
                    'missing_ingredients': [],
                    'substitute_suggestions': {},
                })
        
        return result
    
    except Exception as e:
        return []


def _get_fallback_recipes(ingredients, limit=10):
    """Trả về danh sách công thức hardcoded nếu Gemini fail."""
    # Các công thức mẫu dựa trên nguyên liệu phổ biến
    fallback_recipes = [
        {
            'name': 'Cơm trứng',
            'time': '15 phút',
            'difficulty': 'easy',
            'confidence': 0.8,
            'required_ingredients': ['trứng', 'cơm'],
            'optional_ingredients': ['hành', 'tỏi'],
        },
        {
            'name': 'Trứng chiên',
            'time': '5 phút',
            'difficulty': 'easy',
            'confidence': 0.9,
            'required_ingredients': ['trứng', 'dầu ăn'],
            'optional_ingredients': ['muối', 'hành'],
        },
        {
            'name': 'Canh đơn giản',
            'time': '20 phút',
            'difficulty': 'easy',
            'confidence': 0.75,
            'required_ingredients': ['nước'],
            'optional_ingredients': ['tôm', 'thịt', 'rau'],
        },
        {
            'name': 'Thịt xào hành',
            'time': '15 phút',
            'difficulty': 'medium',
            'confidence': 0.85,
            'required_ingredients': ['thịt heo', 'hành'],
            'optional_ingredients': ['tỏi', 'nước mắm', 'đường'],
        },
    ]
    
    ingredients_lower = [ing.lower() for ing in ingredients]
    matched_recipes = []
    
    for recipe in fallback_recipes:
        required = recipe.get('required_ingredients', [])
        optional = recipe.get('optional_ingredients', [])
        
        # Check required ingredients
        has_required = all(
            any(req.lower() in ing_lower for ing_lower in ingredients_lower)
            for req in required
        )
        
        if has_required:
            # Count optional ingredients
            optional_count = sum(
                1 for opt in optional
                if any(opt.lower() in ing_lower for ing_lower in ingredients_lower)
            )
            
            matched_recipes.append({
                'name': recipe['name'],
                'time': recipe['time'],
                'difficulty': recipe['difficulty'],
                'confidence': recipe['confidence'] + (optional_count * 0.05),  # Bonus
                'missing_ingredients': [],
                'substitute_suggestions': {},
            })
    
    # Sort by difficulty (easy first) và confidence
    matched_recipes = sorted(
        matched_recipes,
        key=lambda r: (r['difficulty'] != 'easy', -r['confidence'])
    )
    
    return matched_recipes[:limit]


def generate_recipe_details(recipe_name, ingredients):
    """
    Generate chi tiết công thức cho một món ăn cụ thể.
    
    Return:
    - {
        'success': bool,
        'recipe': {
            'name': str,
            'servings': int,
            'time_minutes': int,
            'ingredients': [
                {'name': str, 'quantity': str, 'unit': str}
            ],
            'instructions': [str],  # Danh sách bước nấu
            'tips': [str],  # Mẹo nấu
            'nutrition': {
                'calories': float,
                'protein': float,
                'carbs': float,
                'fat': float,
            },
        },
        'message': str,
      }
    """
    if not recipe_name or not ingredients:
        return {
            'success': False,
            'recipe': {},
            'message': 'Tên công thức hoặc nguyên liệu trống',
        }
    
    try:
        recipe_details = _get_recipe_details_from_gemini(recipe_name, ingredients)
        if recipe_details:
            # Try to persist full recipe into DB (Food, Recipe, Ingredients) using helper
            try:
                saved, recipe_id, save_msg = save_full_recipe_to_db(recipe_details, created_by='ai')
                recipe_details['_auto_saved'] = saved
                if recipe_id:
                    recipe_details['_recipe_id'] = recipe_id
                recipe_details['_save_message'] = save_msg
            except Exception as db_err:
                # ignore DB errors — still return generated recipe
                recipe_details['_auto_saved'] = False
                recipe_details['_save_message'] = f'Auto-save failed: {str(db_err)}'

            return {
                'success': True,
                'recipe': recipe_details,
                'message': 'Recipe details generated',
            }

    except RuntimeError as api_err:
        # Handle Gemini API errors (rate limit, auth, etc.)
        error_msg = str(api_err).lower()
        if '429' in error_msg or 'quota' in error_msg or 'rate limit' in error_msg:
            return {
                'success': False,
                'recipe': {},
                'message': f'Gemini API quota exceeded. Please try again later.',
            }
        return {
            'success': False,
            'recipe': {},
            'message': f'Gemini API error: {str(api_err)[:100]}',
        }
    except Exception as err:
        return {
            'success': False,
            'recipe': {},
            'message': f'Could not generate recipe details: {str(err)[:100]}',
        }

    # Fallback (should not reach here)
    return {
        'success': False,
        'recipe': {},
        'message': 'Could not generate recipe details',
    }


# Helper: call Gemini to generate detailed recipe JSON
def _get_recipe_details_from_gemini(recipe_name, ingredients):
    """Gọi Gemini API để tạo chi tiết công thức. Raise exception nếu Gemini lỗi để caller xử lý."""
    try:
        ingredients_str = ', '.join(ingredients)
        prompt = f"""Bạn là đầu bếp chuyên nghiệp người Việt.

Hãy tạo công thức chi tiết cho: "{recipe_name}"
Nguyên liệu có sẵn: {ingredients_str}

Trả về JSON với cấu trúc:
{
  "name": "Tên món",
  "servings": 2,
  "time_minutes": 20,
  "ingredients": [
    {"name": "nguyên liệu", "quantity": "2", "unit": "cái"}
  ],
  "instructions": ["Bước 1", "Bước 2"],
  "tips": ["Mẹo nấu"],
  "nutrition": {"calories": 300, "protein": 15, "carbs": 40, "fat": 8}
}

Chỉ trả về JSON, không có text khác."""

        response_text = _gemini_generate_text(prompt, max_output_tokens=2048)
        if not response_text:
            return None

        # Parse JSON
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if not json_match:
            return None

        json_str = json_match.group(0)
        recipe = json.loads(json_str)

        return recipe

    except RuntimeError:
        # Re-raise Gemini API errors so caller can handle quota/auth issues
        raise
    except Exception:
        # Other parsing errors: return None
        return None


def save_recipe_to_db(recipe_name, instructions, auto_added=False, created_by='ai'):
    """
    Lưu công thức vào database.
    
    Tham số:
    - recipe_name: str - Tên công thức
    - instructions: str - Hướng dẫn nấu
    - auto_added: bool - True nếu auto-save từ AI
    - created_by: str - 'ai', 'manual', hoặc 'api'
    
    Trả về:
    - (success: bool, recipe_id: int or None, message: str)
    """
    try:
        from apps.nutrition.models import Food, FoodCategory, Recipe
        
        # Check if recipe already exists
        existing = Food.objects.filter(name__iexact=recipe_name.strip()).first()
        if existing and hasattr(existing, 'recipe'):
            return True, existing.recipe.id, f'Recipe "{recipe_name}" already exists (ID: {existing.recipe.id})'
        
        # Create new Food entry
        category_obj, _ = FoodCategory.objects.get_or_create(
            name='AI Generated' if created_by == 'ai' else 'Manual'
        )
        food = Food.objects.create(
            name=recipe_name.strip(),
            category=category_obj,
        )
        
        # Create Recipe entry
        recipe = Recipe.objects.create(
            food=food,
            title=recipe_name.strip(),
            instructions=instructions.strip() if instructions else '',
        )
        
        return True, recipe.id, f'Recipe "{recipe_name}" saved successfully (ID: {recipe.id})'
    
    except Exception as e:
        return False, None, f'Error saving recipe: {str(e)}'


def save_recipe_if_good(recipe_dict, confidence_threshold=0.75):
    """
    Tự động lưu công thức nếu đó là một công thức tốt (confidence cao).
    
    Tham số:
    - recipe_dict: dict - Công thức từ recommend_recipes_from_ingredients()
    - confidence_threshold: float - Ngưỡng confidence để auto-save (0-1)
    
    Trả về:
    - (saved: bool, recipe_id: int or None, message: str)
    """
    if not recipe_dict or 'name' not in recipe_dict:
        return False, None, 'Invalid recipe dict'
    
    confidence = recipe_dict.get('confidence', 0)
    
    # Chỉ save nếu confidence đủ cao
    if confidence < confidence_threshold:
        return False, None, f'Confidence {confidence:.2f} < threshold {confidence_threshold}'
    
    recipe_name = recipe_dict.get('name', '')
    # Tạo instructions từ recipe_dict
    instructions = f"""
Tên: {recipe_name}
Thời gian: {recipe_dict.get('time', 'N/A')}
Độ khó: {recipe_dict.get('difficulty', 'medium')}
Độ tin cậy: {confidence:.2f}

Nguyên liệu thiếu: {', '.join(recipe_dict.get('missing_ingredients', [])) or 'Không có'}

Gợi ý: Công thức được tạo tự động từ Gemini AI dựa trên danh sách nguyên liệu của bạn.
    """.strip()
    
    return save_recipe_to_db(
        recipe_name=recipe_name,
        instructions=instructions,
        auto_added=True,
        created_by='ai'
    )


def auto_save_good_recipes(recipes_list, confidence_threshold=0.8):
    """
    Tự động lưu một danh sách công thức tốt vào database.
    
    Tham số:
    - recipes_list: [dict] - Danh sách công thức từ recommend_recipes_from_ingredients()
    - confidence_threshold: float - Ngưỡng confidence để auto-save
    
    Trả về:
    - {
        'total': int,
        'saved': int,
        'failed': int,
        'results': [
            {'name': str, 'saved': bool, 'recipe_id': int or None, 'message': str}
        ]
      }
    """
    results = []
    saved_count = 0
    failed_count = 0
    
    for recipe in recipes_list:
        saved, recipe_id, message = save_recipe_if_good(recipe, confidence_threshold)
        
        results.append({
            'name': recipe.get('name', 'Unknown'),
            'saved': saved,
            'recipe_id': recipe_id,
            'message': message
        })
        
        if saved:
            saved_count += 1
        else:
            failed_count += 1
    
    return {
        'total': len(recipes_list),
        'saved': saved_count,
        'failed': failed_count,
        'results': results
    }


# --- NEW: helpers to persist full recipe details from Gemini into Foods/Recipes/Ingredients ---

def _parse_quantity_to_grams(quantity, unit):
    """Naive parser: try to convert quantity+unit to grams when obvious.
    Returns Decimal grams or None if cannot parse.
    """
    from decimal import Decimal, InvalidOperation

    if quantity is None:
        return None
    try:
        q = Decimal(str(quantity))
    except InvalidOperation:
        # Try to extract number from string
        import re
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)", str(quantity))
        if not m:
            return None
        try:
            q = Decimal(m.group(1))
        except InvalidOperation:
            return None

    unit = (unit or '').strip().lower() if unit else ''
    if unit in ('g', 'gram', 'grams', 'gr') or 'g' in unit:
        return q
    if unit in ('kg', 'kilogram', 'kilograms'):
        return q * Decimal('1000')
    if unit in ('mg', 'milligram', 'milligrams'):
        return q / Decimal('1000')
    # Milliliters/ liters cannot be reliably converted without density; skip
    return None


def _fetch_ingredient_nutrition_from_gemini(ingredient_name):
    """Try to fetch nutrition per 100g for an ingredient from Gemini."""
    try:
        prompt = f"""Bạn là chuyên gia dinh dưỡng.

Trả về thông tin dinh dưỡng cho 100g "{ingredient_name}" dưới dạng JSON:
{{
  "calories": số kcal,
  "protein": số gram,
  "carbs": số gram,
  "fat": số gram,
  "fiber": số gram (nếu có),
  "sodium": số mg (nếu có)
}}

Chỉ trả JSON, không có text khác."""
        
        response_text = _gemini_generate_text(prompt, max_output_tokens=256)
        if not response_text:
            return None
        
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if not json_match:
            return None
        
        nutrition = json.loads(json_match.group(0))
        return nutrition
    except Exception:
        return None


def _calculate_nutrition_from_ingredients(ingredients, gemini_nutrition=None):
    """
    Calculate total nutrition from recipe ingredients.
    
    Falls back to Gemini-provided nutrition if ingredient data incomplete.
    
    Returns:
    - {
        'total': {'calories': float, 'protein': float, ...},
        'per_ingredient': [
            {'name': str, 'quantity_grams': float, 'calories': float, ...}
        ]
      }
    """
    from decimal import Decimal
    from apps.nutrition.models import Ingredient, IngredientNutrition
    
    try:
        total_nutrition = {
            'calories': Decimal('0'),
            'protein': Decimal('0'),
            'carbs': Decimal('0'),
            'fat': Decimal('0'),
            'fiber': Decimal('0'),
            'sodium': Decimal('0'),
        }
        
        per_ingredient = []
        
        for ing in ingredients:
            if not isinstance(ing, dict) or 'name' not in ing:
                continue
            
            name = ing.get('name', '').strip()
            if not name:
                continue
            
            # Parse quantity to grams
            qty = ing.get('quantity')
            unit = ing.get('unit')
            grams = _parse_quantity_to_grams(qty, unit)
            
            if grams is None:
                # Fallback: assume 100g or skip nutrition calc
                grams = Decimal('100')
            
            # Try to find IngredientNutrition from DB
            ing_obj = Ingredient.objects.filter(name__iexact=name).first()
            ing_nutrition = None
            
            if ing_obj and hasattr(ing_obj, 'nutrition'):
                try:
                    ing_nutrition = ing_obj.nutrition
                except Exception:
                    pass
            
            # If not in DB, try Gemini
            if not ing_nutrition:
                ing_nutrition_data = _fetch_ingredient_nutrition_from_gemini(name)
            else:
                ing_nutrition_data = {
                    'calories': float(ing_nutrition.calories) if ing_nutrition.calories else 0,
                    'protein': float(ing_nutrition.protein) if ing_nutrition.protein else 0,
                    'carbs': float(ing_nutrition.carbs) if ing_nutrition.carbs else 0,
                    'fat': float(ing_nutrition.fat) if ing_nutrition.fat else 0,
                    'fiber': float(ing_nutrition.fiber) if ing_nutrition.fiber else 0,
                    'sodium': 0,  # IngredientNutrition doesn't have sodium field
                }
            
            # Calculate actual nutrition for this ingredient amount
            if ing_nutrition_data:
                multiplier = grams / Decimal('100')  # per 100g → per actual amount
                
                ing_entry = {
                    'name': name,
                    'quantity_grams': float(grams),
                    'calories': float(Decimal(str(ing_nutrition_data.get('calories', 0))) * multiplier),
                    'protein': float(Decimal(str(ing_nutrition_data.get('protein', 0))) * multiplier),
                    'carbs': float(Decimal(str(ing_nutrition_data.get('carbs', 0))) * multiplier),
                    'fat': float(Decimal(str(ing_nutrition_data.get('fat', 0))) * multiplier),
                    'fiber': float(Decimal(str(ing_nutrition_data.get('fiber', 0))) * multiplier),
                }
                
                # Add to totals
                try:
                    total_nutrition['calories'] += Decimal(str(ing_entry['calories']))
                    total_nutrition['protein'] += Decimal(str(ing_entry['protein']))
                    total_nutrition['carbs'] += Decimal(str(ing_entry['carbs']))
                    total_nutrition['fat'] += Decimal(str(ing_entry['fat']))
                    total_nutrition['fiber'] += Decimal(str(ing_entry['fiber']))
                except Exception:
                    pass
                
                per_ingredient.append(ing_entry)
            else:
                # No nutrition data available
                per_ingredient.append({
                    'name': name,
                    'quantity_grams': float(grams),
                    'note': 'Nutrition data not available'
                })
        
        # Convert totals to float
        total_nutrition = {
            k: float(v) for k, v in total_nutrition.items()
        }
        
        # If Gemini provided total nutrition, merge/compare
        if gemini_nutrition:
            # Use Gemini as backup/reference
            for key in ('calories', 'protein', 'carbs', 'fat'):
                if key in gemini_nutrition:
                    gemini_val = Decimal(str(gemini_nutrition.get(key, 0)))
                    calc_val = Decimal(str(total_nutrition.get(key, 0)))
                    # If calculated is 0 or missing, use Gemini
                    if calc_val == 0:
                        total_nutrition[key] = float(gemini_val)
        
        return {
            'total': total_nutrition,
            'per_ingredient': per_ingredient
        }
    
    except Exception as e:
        # If calculation fails, return Gemini nutrition or empty
        if gemini_nutrition:
            return {'total': gemini_nutrition, 'per_ingredient': []}
        return {'total': {}, 'per_ingredient': []}


def save_full_recipe_to_db(recipe_dict, created_by='ai'):
    """Persist a full recipe dict (from Gemini) into Food, Recipe and ingredient links.

    Returns (success, recipe_id, message)
    """
    try:
        from decimal import Decimal
        from apps.nutrition.models import Food, FoodCategory, Recipe, Ingredient, FoodIngredient

        if not recipe_dict or 'name' not in recipe_dict:
            return False, None, 'Invalid recipe dict'

        title = (recipe_dict.get('name') or '').strip()
        if not title:
            return False, None, 'Empty recipe name'

        # Category
        category_obj, _ = FoodCategory.objects.get_or_create(
            name='AI Generated' if created_by == 'ai' else 'Manual'
        )

        # Upsert Food
        food = Food.objects.filter(name__iexact=title).first()
        
        # Calculate nutrition from ingredients + merge with Gemini nutrition
        gemini_nutrition = recipe_dict.get('nutrition') or {}
        nutrition_calc = _calculate_nutrition_from_ingredients(
            recipe_dict.get('ingredients') or [],
            gemini_nutrition
        )
        nutrition = nutrition_calc.get('total') or {}
        nutrition_json = nutrition_calc  # Keep full detail (total + per_ingredient)
        
        calories = nutrition.get('calories')
        protein = nutrition.get('protein')
        carbs = nutrition.get('carbs')
        fat = nutrition.get('fat')

        if food:
            # update fields
            food.category = category_obj
            if recipe_dict.get('image_url'):
                food.image_url = recipe_dict.get('image_url')
            # Update nutrition if present
            try:
                if calories is not None:
                    food.calories = Decimal(str(calories))
                if protein is not None:
                    food.protein = Decimal(str(protein))
                if carbs is not None:
                    food.carbs = Decimal(str(carbs))
                if fat is not None:
                    food.fat = Decimal(str(fat))
            except Exception:
                pass
            food.save()
        else:
            food = Food.objects.create(
                name=title,
                category=category_obj,
                image_url=recipe_dict.get('image_url') or None,
                calories=Decimal(str(calories)) if calories is not None else Decimal('0'),
                protein=Decimal(str(protein)) if protein is not None else Decimal('0'),
                carbs=Decimal(str(carbs)) if carbs is not None else Decimal('0'),
                fat=Decimal(str(fat)) if fat is not None else Decimal('0'),
            )

        # Create or update Recipe row
        instructions_list = recipe_dict.get('instructions') or []
        instructions_text = '\n'.join([str(s).strip() for s in instructions_list if s])
        recipe_obj = None
        if hasattr(food, 'recipe') and getattr(food, 'recipe'):
            recipe_obj = food.recipe
            recipe_obj.title = title
            recipe_obj.instructions = instructions_text
            recipe_obj.ingredients_json = recipe_dict.get('ingredients')
            recipe_obj.nutrition_json = nutrition_json  # Use calculated nutrition with detail
            recipe_obj.image_url = recipe_dict.get('image_url') or recipe_obj.image_url
            recipe_obj.source_url = recipe_dict.get('source_url') or recipe_obj.source_url
            recipe_obj.save()
        else:
            recipe_obj = Recipe.objects.create(
                food=food,
                title=title,
                instructions=instructions_text,
                ingredients_json=recipe_dict.get('ingredients') or None,
                nutrition_json=nutrition_json or None,  # Use calculated nutrition with detail
                image_url=recipe_dict.get('image_url') or None,
                source_url=recipe_dict.get('source_url') or None,
            )

        # Ingredients -> create Ingredient and FoodIngredient when quantity in grams is parseable
        ingredients = recipe_dict.get('ingredients') or []
        for ing in ingredients:
            try:
                name = ing.get('name') if isinstance(ing, dict) else str(ing)
                if not name:
                    continue
                name = name.strip()
                ingredient_obj, _ = Ingredient.objects.get_or_create(name=name)

                # try parse grams
                qty = ing.get('quantity') if isinstance(ing, dict) else None
                unit = ing.get('unit') if isinstance(ing, dict) else None
                grams = _parse_quantity_to_grams(qty, unit)
                if grams is not None:
                    # upsert FoodIngredient
                    fi, created = FoodIngredient.objects.get_or_create(
                        food=food,
                        ingredient=ingredient_obj,
                        defaults={'quantity_grams': grams}
                    )
                    if not created:
                        fi.quantity_grams = grams
                        fi.save()
            except Exception:
                # don't fail whole save for ingredient issues
                continue

        return True, recipe_obj.id, f'Recipe "{title}" saved (ID: {recipe_obj.id})'

    except Exception as e:
        return False, None, f'Error saving full recipe: {str(e)}'


