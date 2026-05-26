"""
Module gợi ý biến tấu công thức khi thiếu nguyên liệu.

Mục đích:
- Gợi ý thay thế nguyên liệu (VD: thiếu sữa → thay bằng sữa chua hoặc bỏ)
- Generate công thức biến tấu (modified version)
- Cảnh báo nếu biến tấu ảnh hưởng đến chất lượng món ăn

GHI NHỚ QUAN TRỌNG:
- Luôn có fallback nếu thiếu nguyên liệu "optional"
- Cảnh báo nếu thiếu nguyên liệu "essential" (VD: nước trong canh)
- Biến tấu càng lớn → confidence score càng thấp
"""

import json
import re
from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.services.external_apis import _gemini_generate_text

# Từ điển thay thế nguyên liệu (original → [alternatives])
INGREDIENT_SUBSTITUTES = {
    'sữa': ['sữa chua', 'nước cốt dừa', 'bơ tan'],
    'bơ': ['dầu oliu', 'dầu thực vật'],
    'phô mai': ['sữa chua', 'creme fraiche'],
    'trứng': ['aquafaba (nước đậu)', 'bột lúa mạch'],
    'mì ý': ['mì gạo', 'bánh mì'],
    'tôm': ['cá trắng', 'mực'],
    'thịt heo': ['thịt gà', 'thịt bò', 'đậu'],
    'thịt gà': ['thịt heo', 'thịt bò'],
    'nước mắm': ['xì dầu', 'nước tương'],
    'xì dầu': ['nước tương', 'nước mắm'],
    'hành': ['hành lá', 'tỏi'],
    'tỏi': ['hành', 'gừng'],
    'dầu ăn': ['bơ', 'dầu oliu', 'dầu mè'],
    'muối': [],  # Không thay thế được
    'đường': ['mật ong', 'đường nâu'],
    'bột mì': ['bột ngô', 'bột arrowroot'],
    'cốm': ['gạo nắp', 'mì'],
}

# Phân loại: 'essential' (bắt buộc), 'important' (quan trọng), 'optional' (tùy chọn)
INGREDIENT_CATEGORIES = {
    'muối': 'essential',
    'nước': 'essential',
    'dầu ăn': 'important',
    'trứng': 'important',
    'hành': 'optional',
    'tỏi': 'optional',
    'hành lá': 'optional',
    'nước mắm': 'optional',
}


def suggest_substitutes(missing_ingredient):
    """
    Gợi ý các thay thế cho nguyên liệu bị thiếu.
    
    Tham số:
    - missing_ingredient: str - tên nguyên liệu bị thiếu
    
    Trả về:
    - [str] - danh sách thay thế
    """
    ing_lower = missing_ingredient.lower()
    
    for original, substitutes in INGREDIENT_SUBSTITUTES.items():
        if original.lower() in ing_lower or ing_lower in original.lower():
            return substitutes
    
    return []


def get_ingredient_category(ingredient):
    """
    Lấy danh mục của nguyên liệu (essential/important/optional).
    
    Return: 'essential', 'important', hoặc 'optional' (default)
    """
    ing_lower = ingredient.lower()
    
    for keyword, category in INGREDIENT_CATEGORIES.items():
        if keyword.lower() in ing_lower:
            return category
    
    return 'optional'


def generate_recipe_variations(recipe_name, available_ingredients, missing_ingredients):
    """
    Tạo danh sách công thức biến tấu khi thiếu nguyên liệu.
    
    Tham số:
    - recipe_name: str - tên công thức gốc
    - available_ingredients: [str] - nguyên liệu có sẵn
    - missing_ingredients: [str] - nguyên liệu bị thiếu
    
    Trả về:
    - {
        'success': bool,
        'original_recipe': str,  # Tên công thức gốc
        'variations': [
            {
                'name': str,  # Tên biến tấu
                'missing': [str],  # Nguyên liệu bị thiếu
                'substitutions': {missing_ing: substitute},  # Thay thế gợi ý
                'instructions_changes': [str],  # Thay đổi cách làm
                'impact': str,  # 'minimal', 'medium', 'significant'
                'confidence': float,  # 0-1
            }
        ],
        'message': str,
      }
    """
    if not recipe_name or not missing_ingredients:
        return {
            'success': False,
            'original_recipe': recipe_name or '',
            'variations': [],
            'message': 'Tên công thức hoặc danh sách nguyên liệu thiếu trống',
        }
    
    # Bước 1: Phân loại nguyên liệu thiếu
    critical_missing = []
    optional_missing = []
    
    for ing in missing_ingredients:
        category = get_ingredient_category(ing)
        if category == 'essential':
            critical_missing.append(ing)
        else:
            optional_missing.append(ing)
    
    # Nếu thiếu nguyên liệu essential, chỉ có thể bỏ qua hoặc thay thế
    variations = []
    
    # Variation 1: Bỏ qua (bỏ các nguyên liệu optional)
    if optional_missing:
        variations.append({
            'name': f"{recipe_name} (không {', '.join(optional_missing)})",
            'missing': optional_missing,
            'substitutions': {},
            'instructions_changes': [f"Bỏ qua {', '.join(optional_missing)}"],
            'impact': 'minimal' if len(optional_missing) <= 1 else 'medium',
            'confidence': 0.8 - len(optional_missing) * 0.1,
        })
    
    # Variation 2: Thay thế
    substitutions = {}
    for ing in missing_ingredients:
        substitutes = suggest_substitutes(ing)
        if substitutes:
            substitutions[ing] = substitutes[0]  # Lấy thay thế đầu tiên
    
    if substitutions:
        sub_list = [f"{old} → {new}" for old, new in substitutions.items()]
        variations.append({
            'name': f"{recipe_name} (biến tấu)",
            'missing': missing_ingredients,
            'substitutions': substitutions,
            'instructions_changes': [f"Thay thế: {', '.join(sub_list)}"],
            'impact': 'medium' if len(substitutions) <= 1 else 'significant',
            'confidence': 0.7 - len(substitutions) * 0.15,
        })
    
    # Gọi Gemini để tạo biến tấu thêm
    if GEMINI_API_KEY and GEMINI_MODEL:
        gemini_variations = _get_gemini_variations(
            recipe_name, available_ingredients, missing_ingredients
        )
        variations.extend(gemini_variations)
    
    return {
        'success': len(variations) > 0,
        'original_recipe': recipe_name,
        'variations': variations,
        'message': f'Generated {len(variations)} recipe variations',
    }


def _get_gemini_variations(recipe_name, available_ingredients, missing_ingredients):
    """Gọi Gemini API để tạo biến tấu sáng tạo."""
    try:
        available_str = ', '.join(available_ingredients)
        missing_str = ', '.join(missing_ingredients)
        
        prompt = f"""Bạn là đầu bếp chuyên nghiệp.

Công thức gốc: {recipe_name}
Nguyên liệu có sẵn: {available_str}
Nguyên liệu bị thiếu: {missing_str}

Hãy gợi ý 2-3 cách biến tấu sáng tạo để làm {recipe_name} mà không cần {missing_str}.

Trả về JSON:
[
  {{
    "name": "Tên biến tấu",
    "substitutions": {{"missing_ing": "substitute"}},
    "instructions_changes": ["Bước thay đổi"],
    "impact": "minimal/medium/significant",
    "confidence": 0.8
  }}
]

Chỉ trả về JSON, không có text khác."""

        response_text = _gemini_generate_text(prompt, max_output_tokens=1024)
        if not response_text:
            return []
        
        # Parse JSON
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if not json_match:
            return []
        
        json_str = json_match.group(0)
        variations = json.loads(json_str)
        
        return variations if isinstance(variations, list) else []
    
    except Exception as e:
        return []


def get_substitution_warnings(available_ingredients, missing_ingredients):
    """
    Cảnh báo nếu thiếu nguyên liệu quan trọng.
    
    Return:
    - {
        'warnings': [str],
        'can_make_recipe': bool,
      }
    """
    warnings = []
    
    for ing in missing_ingredients:
        category = get_ingredient_category(ing)
        
        if category == 'essential':
            warnings.append(
                f"[WARNING] THIẾU NGUYÊN LIỆU QUAN TRỌNG: '{ing}'. Công thức sẽ bị thay đổi đáng kể."
            )
        elif category == 'important':
            warnings.append(
                f"[WARNING] Thiếu '{ing}'. Kết quả có thể không hoàn hảo."
            )
    
    can_make = len([ing for ing in missing_ingredients if get_ingredient_category(ing) == 'essential']) < 3
    
    return {
        'warnings': warnings,
        'can_make_recipe': can_make,
    }
