"""
Module tạo danh sách mua sắm từ Meal Plan.

Mục đích:
- Lấy MealPlan của user trong khoảng thời gian
- Trích xuất tất cả FoodIngredient từ các Food trong MealPlan
- Tính tổng lượng nguyên liệu cần thiết (servings × quantity)
- Gộp và optimize danh sách mua sắm

GHI NHỚ QUAN TRỌNG:
- Dữ liệu động từ CSDL (MealPlan, Food, FoodIngredient, Ingredient)
- Tính toán chính xác: servings × quantity = tổng cần dùng
- Gộp các ingredient cùng loại → tránh duplicate
- Danh sách phải practical (ví dụ: 50g + 100g = 150g, không phải "2 items")
"""

from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict

from django.db.models import F, Sum, DecimalField, Q
from django.db.models.functions import Cast

from apps.meal_plans.models import MealPlan
from apps.nutrition.models import Food, FoodIngredient, Ingredient, IngredientPrice


def generate_shopping_list_from_meal_plan(account, date_start=None, date_end=None, budget=None):
    """
    Tạo danh sách mua sắm từ Meal Plan của user.
    
    Tham số:
    - account: Account object
    - date_start: Ngày bắt đầu (default: hôm nay)
    - date_end: Ngày kết thúc (default: 7 ngày tới)
    
    Trả về:
    - {
        'success': bool,
        'shopping_items': [
            {
                'ingredient_id': int,
                'ingredient_name': str,
                'total_quantity': float,
                'unit': str,  # 'g', 'ml', 'cái', etc.
                'meals': [
                    {'food_name': str, 'date': str, 'quantity': float}
                ]
            }
        ],
        'meal_plan_count': int,
        'date_range': {'start': str, 'end': str},
        'message': str,
      }
    """
    if not account:
        return {
            'success': False,
            'shopping_items': [],
            'meal_plan_count': 0,
            'date_range': {},
            'message': 'Account is required',
        }
    
    # Bước 1: Set default date range
    if not date_start:
        date_start = date.today()
    if not date_end:
        date_end = date_start + timedelta(days=7)
    
    # Convert to string format if needed
    if isinstance(date_start, date):
        date_start_str = date_start.isoformat()
    else:
        date_start_str = str(date_start)
    
    if isinstance(date_end, date):
        date_end_str = date_end.isoformat()
    else:
        date_end_str = str(date_end)
    
    # Bước 2: Lấy MealPlan trong khoảng thời gian
    meal_plans = MealPlan.objects.filter(
        account=account,
        date__gte=date_start_str,
        date__lte=date_end_str,
    ).select_related('food')
    
    meal_plan_count = meal_plans.count()
    
    if meal_plan_count == 0:
        return {
            'success': True,
            'shopping_items': [],
            'meal_plan_count': 0,
            'date_range': {'start': date_start_str, 'end': date_end_str},
            'message': 'No meal plans found in date range',
        }
    
    # Bước 3: Tính tổng nguyên liệu cần thiết
    # Dùng dictionary để gộp theo ingredient
    ingredient_totals = defaultdict(lambda: {
        'ingredient_id': None,
        'ingredient_name': '',
        'total_quantity': Decimal('0'),
        'unit': '',
        'meals': [],
    })
    
    for meal_plan in meal_plans:
        food = meal_plan.food
        servings = Decimal(str(meal_plan.servings))  # Convert to Decimal
        
        # Lấy tất cả FoodIngredient cho Food này
        food_ingredients = FoodIngredient.objects.filter(
            food=food
        ).select_related('ingredient')
        
        for food_ingredient in food_ingredients:
            ingredient = food_ingredient.ingredient
            quantity = Decimal(str(food_ingredient.quantity or 0))
            
            # Tính tổng cần dùng
            total_needed = servings * quantity
            
            ingredient_key = ingredient.id
            
            # Cộng dồn số lượng
            ingredient_totals[ingredient_key]['ingredient_id'] = ingredient.id
            ingredient_totals[ingredient_key]['ingredient_name'] = ingredient.name
            ingredient_totals[ingredient_key]['total_quantity'] += total_needed
            
            # Default unit (nên lưu unit trong FoodIngredient nhưng hiện tại chưa có)
            if not ingredient_totals[ingredient_key]['unit']:
                ingredient_totals[ingredient_key]['unit'] = _guess_unit_from_ingredient_name(
                    ingredient.name
                )
            
            # Ghi lại chi tiết từng meal (để traceability)
            ingredient_totals[ingredient_key]['meals'].append({
                'food_name': food.name,
                'date': meal_plan.date,
                'quantity': float(total_needed),
            })
    
    # Bước 4: Format output
    shopping_items = []
    for ingredient_id, item_data in ingredient_totals.items():
        if ingredient_id is not None:
            shopping_items.append({
                'ingredient_id': item_data['ingredient_id'],
                'ingredient_name': item_data['ingredient_name'],
                'total_quantity': float(item_data['total_quantity']),
                'unit': item_data['unit'],
                'meals': item_data['meals'],
            })

    # Sort by ingredient name (dễ đọc)
    shopping_items = _normalize_shopping_items(shopping_items)
    shopping_items = sorted(shopping_items, key=lambda x: x['ingredient_name'].lower())

    result = {
        'success': True,
        'shopping_items': shopping_items,
        'meal_plan_count': meal_plan_count,
        'date_range': {'start': date_start_str, 'end': date_end_str},
        'message': f'Generated shopping list from {meal_plan_count} meal plans',
    }

    if budget is not None:
        cost_result = calculate_shopping_cost_estimate(shopping_items)
        budget_decimal = Decimal(str(budget))
        total_cost = Decimal(str(cost_result['total_cost']))
        result['estimated_cost'] = float(total_cost)
        result['cost_breakdown'] = cost_result
        result['budget'] = float(budget_decimal)
        result['budget_ok'] = total_cost <= budget_decimal
        result['budget_shortfall'] = float(max(total_cost - budget_decimal, Decimal('0')))
        result['budget_suggestions'] = _suggest_budget_adjustments(shopping_items, budget_decimal)

    return result


def _normalize_shopping_items(shopping_items):
    """Chuẩn hoá đơn vị và định dạng danh sách mua sắm."""
    normalized = []
    for item in shopping_items:
        unit = item.get('unit') or 'g'
        total_quantity = Decimal(str(item.get('total_quantity') or 0))

        if unit == 'g' and total_quantity >= Decimal('1000'):
            total_quantity = total_quantity / Decimal('1000')
            unit = 'kg'
        elif unit == 'ml' and total_quantity >= Decimal('1000'):
            total_quantity = total_quantity / Decimal('1000')
            unit = 'l'

        processed_meals = []
        for meal in item.get('meals', []):
            meal_quantity = Decimal(str(meal.get('quantity') or 0))
            if unit == 'kg' and item.get('unit') == 'g':
                meal_quantity = meal_quantity / Decimal('1000')
            elif unit == 'l' and item.get('unit') == 'ml':
                meal_quantity = meal_quantity / Decimal('1000')
            processed_meals.append({
                'food_name': meal.get('food_name'),
                'date': meal.get('date'),
                'quantity': float(meal_quantity),
            })

        normalized.append({
            'ingredient_id': item['ingredient_id'],
            'ingredient_name': item['ingredient_name'],
            'total_quantity': float(total_quantity),
            'unit': unit,
            'meals': processed_meals,
        })
    return normalized


def _guess_unit_from_ingredient_name(ingredient_name):
    """
    Dự đoán đơn vị dựa trên tên nguyên liệu (heuristic).
    
    VD: 'trứng' → 'cái', 'dầu ăn' → 'ml', 'bột mì' → 'g'
    """
    if not ingredient_name:
        return 'g'

    ing_lower = ingredient_name.lower()
    
    # Phân loại đơn vị thông thường
    egg_keywords = ['trứng', 'egg', 'quả']
    liquid_keywords = ['dầu', 'nước', 'sữa', 'ml', 'oil', 'juice', 'sauce']
    piece_keywords = ['hành', 'tỏi', 'ớt', 'cà chua', 'onion', 'garlic', 'pepper', 'tomato']
    
    for keyword in egg_keywords:
        if keyword in ing_lower:
            return 'cái'
    
    for keyword in liquid_keywords:
        if keyword in ing_lower:
            return 'ml'
    
    for keyword in piece_keywords:
        if keyword in ing_lower:
            return 'cái'
    
    # Default: grams
    return 'g'


def _normalize_quantity(quantity, unit):
    unit = (unit or '').lower()
    quantity = Decimal(str(quantity or 0))
    if unit == 'kg':
        return quantity * Decimal('1000'), 'g'
    if unit == 'l':
        return quantity * Decimal('1000'), 'ml'
    return quantity, unit or 'g'


def _ingredient_name_key(name):
    return (name or '').strip().lower()


def _suggest_budget_adjustments(shopping_items, budget):
    suggestions = []
    if budget is None:
        return suggestions

    total_cost = Decimal(str(calculate_shopping_cost_estimate(shopping_items)['total_cost']))
    budget_decimal = Decimal(str(budget))
    if total_cost > budget_decimal:
        suggestions.append('Ngân sách hiện tại không đủ, hãy cân nhắc giảm nguyên liệu không quan trọng.')
        suggestions.append('Thay thế nguyên liệu đắt bằng các loại rẻ hơn hoặc ưu tiên món rẻ hơn.')
        suggestions.append('Có thể chọn lại món ăn trong thực đơn để phù hợp với ngân sách.')
    else:
        suggestions.append('Ngân sách đủ cho danh sách mua sắm hiện tại.')
    return suggestions


def calculate_shopping_cost_estimate(shopping_items, market_data=None):
    """
    Tính toán chi phí ước tính của danh sách mua sắm.
    Ưu tiên dữ liệu giá từ DB IngredientPrice, fallback về default prices.
    
    Tham số:
    - shopping_items: [dict] - danh sách từ generate_shopping_list_from_meal_plan()
    - market_data: {ingredient_name: price_per_unit} - dữ liệu giá (optional)
    
    Trả về:
    - {
        'total_cost': float,
        'items_with_cost': [
            {
                'ingredient_name': str,
                'ingredient_id': int,
                'quantity': float,
                'unit': str,
                'unit_price': float,
                'total_price': float,
            }
        ],
        'note': str,
      }
    """
    items_with_cost = []
    total_cost = 0
    
    for item in shopping_items:
        ing_id = item.get('ingredient_id')
        ing_name = item['ingredient_name']
        quantity = item['total_quantity']
        unit = item['unit']
        
        # BƯỚC 1: Thử lấy giá từ database IngredientPrice
        unit_price = None
        if ing_id:
            try:
                price_obj = IngredientPrice.objects.filter(ingredient_id=ing_id).first()
                if price_obj:
                    # Chuyển đổi đơn vị nếu cần (DB lưu per unit_type của nó)
                    unit_price = float(price_obj.price_per_unit)
                    # Nếu unit_type là 'kg' nhưng shopping list dùng 'g', chia cho 1000
                    if 'kg' in price_obj.unit_type.lower() and unit == 'g':
                        unit_price = unit_price / 1000
            except Exception:
                pass
        
        # BƯỚC 2: Fallback về default prices nếu không có trong DB
        if unit_price is None:
            if market_data is None:
                market_data = _get_default_market_prices()
            
            ing_name_lower = ing_name.lower()
            for keyword, price in market_data.items():
                if keyword in ing_name_lower:
                    unit_price = price
                    break
        
        # BƯỚC 3: Dùng giá default nếu vẫn không tìm thấy
        if unit_price is None:
            unit_price = 5000  # Default VND per unit
        
        total_price = quantity * unit_price
        total_cost += total_price
        
        items_with_cost.append({
            'ingredient_name': ing_name,
            'ingredient_id': ing_id,
            'quantity': quantity,
            'unit': unit,
            'unit_price': unit_price,
            'total_price': total_price,
        })
    
    return {
        'total_cost': total_cost,
        'items_with_cost': items_with_cost,
        'note': 'Chi phí ước tính: ưu tiên dữ liệu từ DB IngredientPrice, fallback giá thị trường mặc định',
    }


def _get_default_market_prices():
    """Giá thị trường mặc định (VND)."""
    return {
        'trứng': 2500,      # VND/quả
        'thịt heo': 80000,  # VND/kg → 80 VND/g
        'thịt gà': 60000,
        'cá': 100000,
        'tôm': 150000,
        'dầu ăn': 150,      # VND/ml
        'nước': 1,
        'muối': 10,
        'đường': 15,
        'nước mắm': 200,
        'hành': 5000,       # VND/quả
        'tỏi': 2000,
        'cà chua': 5000,
        'rau': 3000,
        'khoai': 2000,
    }


def suggest_shopping_optimization(shopping_items):
    """
    Gợi ý tối ưu hóa danh sách mua sắm.
    
    VD:
    - Mua "cộng lại" thay vì split nhỏ
    - Gợi ý mua combo nếu có
    - Warning nếu hạn dùng ngắn
    
    Return:
    - {
        'suggestions': [str],
        'optimization_tips': [str],
      }
    """
    suggestions = []
    optimization_tips = []
    
    # Gợi ý tối ưu hóa
    for item in shopping_items:
        quantity = item['total_quantity']
        unit = item['unit']
        
        if unit == 'g' and quantity > 1000:
            # Nên mua theo kg
            kg_qty = quantity / 1000
            suggestions.append(
                f"Mua {item['ingredient_name']}: {kg_qty:.1f} kg (thay vì {quantity:.0f}g)"
            )
        
        if unit == 'ml' and quantity > 1000:
            # Nên mua theo lít
            liter_qty = quantity / 1000
            suggestions.append(
                f"Mua {item['ingredient_name']}: {liter_qty:.1f} lít (thay vì {quantity:.0f}ml)"
            )
    
    if not suggestions:
        optimization_tips.append("Danh sách mua sắm đã được tối ưu hóa")
    
    optimization_tips.append("Hãy mua nguyên liệu tươi nhất (kiểm tra ngày hạn)")
    optimization_tips.append("Nên mua tại một siêu thị duy nhất để tiết kiệm thời gian")
    
    return {
        'suggestions': suggestions,
        'optimization_tips': optimization_tips,
    }
