"""
Service cung cấp dữ liệu giá nguyên liệu từ database.

Mục đích:
- Truy vấn giá thực từ bảng IngredientPrice
- Phát hiện câu hỏi về giá trong chat
- Cung cấp dữ liệu giá chính xác cho AI khi trả lời
- Tránh AI trả lời chung chung về giá
"""

import re
from decimal import Decimal
from typing import List, Dict, Optional

from apps.nutrition.models import Ingredient, IngredientPrice


def _is_price_related_question(text: str) -> bool:
    """
    Kiểm tra xem câu hỏi có liên quan đến giá không.
    
    Return: True nếu câu hỏi là về giá, False nếu không
    """
    if not text:
        return False
    
    text_lower = text.lower()
    
    # Các keyword về giá
    price_keywords = [
        'giá', 'giá bao nhiêu', 'bao nhiêu tiền', 'chi phí', 'cost',
        'giá cả', 'giá thị trường', 'tính tiền', 'bao nhiêu', 'mua',
        'mắc', 'rẻ', 'đắt', 'ngân sách', 'dự toán', 'ngân sách',
        'price', 'cost estimate', 'budget', 'expensive', 'cheap',
    ]
    
    for keyword in price_keywords:
        if keyword in text_lower:
            return True
    
    return False


def extract_ingredient_names_from_question(text: str) -> List[str]:
    """
    Trích xuất tên nguyên liệu từ câu hỏi của người dùng.
    
    VD: "Giá ức gà bao nhiêu?" → ["ức gà", "gà"]
    
    Return: list tên nguyên liệu
    """
    if not text:
        return []
    
    # Các pattern chung cho tên nguyên liệu
    # Đơn giản: word tokens giữa các từ khóa giá
    price_keywords = [
        'giá', 'bao nhiêu', 'cost', 'price',
        'của', 'cái', 'chiếc', 'kg', 'gam', 'cân'
    ]
    
    text_lower = text.lower()
    
    # Lọc từ không phải là price keywords
    words = text_lower.split()
    candidates = []
    
    for word in words:
        word_clean = word.strip('.,!?;:')
        if word_clean and word_clean not in price_keywords and len(word_clean) > 2:
            candidates.append(word_clean)
    
    return candidates


def get_ingredient_prices(ingredient_names: List[str], limit: int = 10) -> Dict:
    """
    Lấy dữ liệu giá từ database cho các nguyên liệu.
    
    Tham số:
    - ingredient_names: [str] - danh sách tên nguyên liệu cần tìm
    - limit: số lượng kết quả trả về tối đa
    
    Return: {
        'found': [
            {
                'ingredient_name': str,
                'price_per_unit': float,
                'unit_type': str,
                'updated_at': str,
            }
        ],
        'not_found': [str],  # nguyên liệu không tìm thấy giá
        'total_found': int,
    }
    """
    found = []
    not_found = []
    
    for ing_name in ingredient_names:
        if not ing_name or len(ing_name) < 2:
            continue
        
        # Tìm ingredient match
        ingredient = Ingredient.objects.filter(
            name__icontains=ing_name,
            is_deleted=False
        ).first()
        
        if not ingredient:
            not_found.append(ing_name)
            continue
        
        # Lấy giá cho ingredient
        price_obj = IngredientPrice.objects.filter(
            ingredient=ingredient
        ).first()
        
        if not price_obj:
            not_found.append(ing_name)
            continue
        
        found.append({
            'ingredient_name': ingredient.name,
            'ingredient_id': ingredient.id,
            'price_per_unit': float(price_obj.price_per_unit),
            'unit_type': price_obj.unit_type,
            'updated_at': price_obj.updated_at.isoformat() if price_obj.updated_at else None,
        })
    
    return {
        'found': found[:limit],
        'not_found': not_found,
        'total_found': len(found),
    }


def format_price_info_for_ai(price_data: Dict) -> str:
    """
    Format dữ liệu giá thành chuỗi để đưa vào system context cho AI.
    
    Return: string mô tả giá các nguyên liệu
    """
    if not price_data.get('found'):
        return "Không có dữ liệu giá từ database cho các nguyên liệu này."
    
    lines = ["DỮ LIỆU GIÁ NGUYÊN LIỆU TỪ DATABASE:"]
    
    for item in price_data['found']:
        ing_name = item['ingredient_name']
        price = item['price_per_unit']
        unit = item['unit_type']
        updated = item.get('updated_at', 'N/A')
        
        lines.append(f"- {ing_name}: {price:,.0f} VNĐ/{unit} (cập nhật: {updated})")
    
    if price_data.get('not_found'):
        lines.append("\nChưa có dữ liệu giá cho:")
        for ing_name in price_data['not_found']:
            lines.append(f"- {ing_name}")
    
    return "\n".join(lines)


def get_ai_price_context(user_question: str) -> Optional[str]:
    """
    Lấy context giá từ database nếu câu hỏi là về giá.
    
    Logic:
    1. Kiểm tra câu hỏi có liên quan đến giá không
    2. Nếu có → trích xuất tên nguyên liệu
    3. Truy vấn giá từ database
    4. Format thành context cho AI
    
    Return: context string hoặc None nếu không phải câu hỏi về giá
    """
    # Bước 1: Check nếu không phải câu hỏi về giá
    if not _is_price_related_question(user_question):
        return None
    
    # Bước 2: Trích xuất tên nguyên liệu
    ing_names = extract_ingredient_names_from_question(user_question)
    if not ing_names:
        return None
    
    # Bước 3: Truy vấn giá từ database
    price_data = get_ingredient_prices(ing_names)
    
    # Bước 4: Format context
    return format_price_info_for_ai(price_data)


def get_all_ingredient_prices() -> List[Dict]:
    """
    Lấy tất cả dữ liệu giá từ database.
    
    Return: list các nguyên liệu có giá
    """
    prices = []
    for price_obj in IngredientPrice.objects.select_related('ingredient').all():
        prices.append({
            'ingredient_name': price_obj.ingredient.name,
            'ingredient_id': price_obj.ingredient.id,
            'price_per_unit': float(price_obj.price_per_unit),
            'unit_type': price_obj.unit_type,
            'updated_at': price_obj.updated_at.isoformat() if price_obj.updated_at else None,
        })
    return prices
