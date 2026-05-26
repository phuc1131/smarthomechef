"""
Module phân tích và trích xuất nguyên liệu từ text tiếng Việt tự nhiên.

Mục đích:
- Parse nguyên liệu từ câu chat như: "Tôi có trứng, thịt heo, hành"
- Dùng Gemini API để nhận diện nguyên liệu chính xác
- Trả về danh sách chuẩn hóa các nguyên liệu

GHI NHỚ QUAN TRỌNG:
- Dùng Gemini vì hiểu ngữ cảnh tiếng Việt tốt
- Fallback: nếu AI không available, dùng keyword matching
- Chuẩn hóa tên nguyên liệu về dạng cơ sở (VD: "thịt lợn" → "thịt heo")
- Cache kết quả để tránh gọi API nhiều lần
"""

import json
import re
from app.config import GEMINI_API_KEY, GEMINI_MODEL
from apps.nutrition.models import IngredientAlias
from app.services.external_apis import _gemini_generate_text


# Từ điển chuẩn hóa nguyên liệu (aliases → canonical name)
INGREDIENT_ALIASES = {
    'trứng': ['trứng gà', 'quả trứng', 'egg', 'eggs'],
    'thịt heo': ['thịt lợn', 'thịt hog', 'pork'],
    'thịt gà': ['gà', 'chicken', 'gà tây'],
    'thịt bò': ['bò', 'beef', 'thịt đỏ'],
    'cá hồi': ['salmon', 'cá hồi tươi', 'cá hồi muối'],
    'tôm': ['tôm sú', 'tôm tươi', 'shrimp', 'prawn'],
    'cà chua': ['cà chua tươi', 'tomato', 'xà chua'],
    'hành': ['hành tây', 'onion', 'hành khô'],
    'tỏi': ['tỏi tươi', 'garlic', 'tỏi ươn'],
    'hành lá': ['hành xanh', 'scallion', 'spring onion'],
    'dầu ăn': ['dầu thực vật', 'oil', 'dầu tây'],
    'muối': ['muối trắng', 'salt'],
    'nước mắm': ['nước cốt cá', 'fish sauce'],
    'đường': ['đường trắng', 'sugar', 'đường cát'],
    'bột mì': ['bột lúa mì', 'flour', 'bột gạo'],
    'cơm': ['gạo', 'rice', 'cơm tấm'],
    'bánh mì': ['bánh', 'bread', 'baguette'],
    'rau diếp': ['rau mầm', 'greens', 'lettuce'],
    'xà lách': ['xà lách tươi', 'salad', 'lettuce'],
    'dưa chuột': ['oạc', 'cucumber', 'dưa leo'],
    'cà rốt': ['cà rốt tươi', 'carrot', 'súp lơ'],
    'khoai tây': ['khoai tây tươi', 'potato', 'khoai lang'],
    'sữa': ['sữa tươi', 'milk', 'sữa chua'],
    'phô mai': ['cheese', 'pho mat', 'cheese'],
    'bơ': ['bơ đậu phộng', 'butter', 'peanut butter'],
    'nước': ['nước lọc', 'water', 'nước sôi'],
}

# Keyword hardcoded để detect ingredients nếu Gemini fail
INGREDIENT_KEYWORDS = [
    'trứng', 'thịt', 'gà', 'bò', 'heo', 'lợn', 'cá', 'tôm', 'cua',
    'cà chua', 'hành', 'tỏi', 'hành lá', 'dưa', 'cà rốt', 'khoai',
    'rau', 'xà lách', 'diếp', 'cối', 'dưa chuột', 'ớt',
    'bột', 'bánh mì', 'gạo', 'cơm', 'mì', 'noodle', 'pasta',
    'dầu', 'muối', 'đường', 'nước mắm', 'sốt', 'nước tương',
    'sữa', 'phô mai', 'bơ', 'kem',
    'chuối', 'dâu', 'nho', 'cam', 'chanh', 'dừa',
    'đậu', 'lạc', 'hạt', 'óc chó',
    'tương', 'tỏi tây', 'xà phòng', 'miso',
]


def _normalize_ingredient_name(name):
    """
    Chuẩn hóa tên nguyên liệu về dạng chính tắc.
    
    VD: "thịt lợn" → "thịt heo", "gà mái" → "thịt gà"
    """
    name_lower = name.strip().lower()

    # Check database alias table first
    try:
        alias_row = IngredientAlias.objects.filter(alias__iexact=name_lower).select_related('ingredient').first()
        if alias_row and alias_row.ingredient and alias_row.ingredient.name:
            return alias_row.ingredient.name
    except Exception:
        pass

    # Check aliases
    for canonical, aliases_list in INGREDIENT_ALIASES.items():
        if name_lower == canonical.lower():
            return canonical
        for alias in aliases_list:
            if name_lower == alias.lower() or name_lower in alias.lower():
                return canonical
    
    return name.strip()  # Trả về tên gốc nếu không tìm được chuẩn hóa


def _extract_ingredients_from_text_fallback(text):
    """
    Fallback method: keyword matching khi Gemini không available.
    Tìm các keywords trong text và return danh sách.
    """
    text_lower = text.lower()
    found_ingredients = set()
    
    for keyword in INGREDIENT_KEYWORDS:
        if keyword in text_lower:
            normalized = _normalize_ingredient_name(keyword)
            found_ingredients.add(normalized)
    
    return list(found_ingredients)


def parse_ingredients_from_text(user_text):
    """
    Parse nguyên liệu từ text tiếng Việt tự nhiên.
    
    Tham số:
    - user_text: Văn bản từ user, VD: "Tôi có trứng, thịt heo, hành"
    
    Trả về:
    - {
        'success': bool,
        'ingredients': [str],  # Danh sách nguyên liệu chuẩn hóa
        'raw_ingredients': [str],  # Danh sách nguyên liệu từ AI trước khi chuẩn hóa
        'confidence': float,  # 0-1, độ tin cậy kết quả
        'method': str,  # 'gemini', 'fallback', 'error'
        'message': str,  # Thông báo thêm
      }
    
    GHI NHỚ:
    - Luôn return structured dict, không throw exception
    - Confidence thấp nếu fallback method
    - Duplicate ingredients sẽ bị loại bỏ
    """
    if not user_text or not user_text.strip():
        return {
            'success': False,
            'ingredients': [],
            'raw_ingredients': [],
            'confidence': 0.0,
            'method': 'error',
            'message': 'Text trống',
        }
    
    # Bước 1: Try Gemini API
    if GEMINI_API_KEY and GEMINI_MODEL:
        try:
            gemini_response = _extract_ingredients_gemini(user_text)
            if gemini_response.get('success'):
                # Chuẩn hóa các nguyên liệu từ Gemini
                raw_ingredients = gemini_response.get('ingredients', [])
                normalized_ingredients = [
                    _normalize_ingredient_name(ing) for ing in raw_ingredients
                ]
                # Loại bỏ duplicates, preserve order
                seen = set()
                unique_ingredients = []
                for ing in normalized_ingredients:
                    if ing.lower() not in seen:
                        seen.add(ing.lower())
                        unique_ingredients.append(ing)
                
                return {
                    'success': True,
                    'ingredients': unique_ingredients,
                    'raw_ingredients': raw_ingredients,
                    'confidence': gemini_response.get('confidence', 0.85),
                    'method': 'gemini',
                    'message': f'Found {len(unique_ingredients)} ingredients',
                }
        except Exception as e:
            # Fallback nếu Gemini fail
            pass
    
    # Bước 2: Fallback - keyword matching
    fallback_ingredients = _extract_ingredients_from_text_fallback(user_text)
    
    return {
        'success': len(fallback_ingredients) > 0,
        'ingredients': fallback_ingredients,
        'raw_ingredients': fallback_ingredients,
        'confidence': 0.5 if fallback_ingredients else 0.0,
        'method': 'fallback',
        'message': f'Found {len(fallback_ingredients)} ingredients (fallback)',
    }


def _extract_ingredients_gemini(user_text):
    """
    Gọi Gemini API để trích xuất nguyên liệu từ text tiếng Việt.
    
    Prompt: Yêu cầu Gemini liệt kê các nguyên liệu từ text user.
    Output: JSON array của tên nguyên liệu.
    """
    try:
        prompt = f"""Bạn là chuyên gia phân tích nguyên liệu nấu ăn.

Người dùng vừa nói: "{user_text}"

Hãy trích xuất danh sách nguyên liệu/thực phẩm từ câu nói trên.

Yêu cầu:
1. Trả về JSON array chỉ chứa tên nguyên liệu (string)
2. Mỗi nguyên liệu là 1 item trong array
3. Không thêm số lượng, đơn vị, hay mô tả
4. Chỉ trả về JSON, không có text khác

Ví dụ:
- Input: "Tôi có trứng, thịt heo, hành"
- Output: ["trứng", "thịt heo", "hành"]

- Input: "Làm cháo từ gạo, gà và hành tây"
- Output: ["gạo", "gà", "hành tây"]

Hãy trích xuất nguyên liệu từ: "{user_text}"

Trả về JSON array:"""

        response_text = _gemini_generate_text(prompt)
        if not response_text:
            return {'success': False, 'ingredients': []}
        
        # Parse JSON từ response
        # Thường Gemini trả về format: [item1, item2, ...] hoặc ```json\n[...]\n```
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if not json_match:
            return {'success': False, 'ingredients': []}
        
        json_str = json_match.group(0)
        ingredients = json.loads(json_str)
        
        # Validate output format
        if not isinstance(ingredients, list):
            return {'success': False, 'ingredients': []}
        
        # Filter string items
        ingredients = [str(ing).strip() for ing in ingredients if ing]
        
        return {
            'success': True,
            'ingredients': ingredients,
            'confidence': 0.9,
        }
    
    except json.JSONDecodeError:
        return {'success': False, 'ingredients': []}
    except Exception as e:
        return {'success': False, 'ingredients': []}

