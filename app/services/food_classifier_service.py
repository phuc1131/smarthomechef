"""
Food Classifier Bot - Phân biệt Ingredient vs Food

INGREDIENT (Nguyên Liệu):
  - Chỉ có vitamin, mineral, fiber (KHÔNG có calories)
  - Ví dụ: muối, baking powder, xác định, gia vị
  
FOOD (Đồ Ăn):
  - Có calories + macros (protein, carbs, fat)
  - Có dinh dưỡng chi tiết (vitamins, minerals, fiber)
  - Ví dụ: cơm, mì, thịt gà, rau xanh
"""

import re
from typing import Literal, Dict, Any
from decimal import Decimal


class FoodClassifier:
    """Bot phân biệt ingredient vs food"""
    
    # Danh sách keyword nguyên liệu
    INGREDIENT_KEYWORDS = [
        'muối', 'baking powder', 'baking soda', 'đường', 'gia vị', 'mắm', 'tương',
        'dầu ăn', 'nước mắm', 'nước tương', 'hạt nêm', 'bột', 'tinh bột', 'lòng trắng trứng',
        'nước chanh', 'giấm', 'xi dầu', 'nước cốt dừa', 'sữa đặc', 'sữa tươi',
        'xà phòng', 'chất tẩy', 'enzyme', 'preservative', 'additive', 'flavoring',
        'essence', 'extract', 'powder', 'flour', 'spice', 'seasoning', 'condiment'
    ]
    
    # Danh sách keyword đồ ăn
    FOOD_KEYWORDS = [
        'cơm', 'mì', 'bánh', 'thịt', 'cá', 'tôm', 'cua', 'rau', 'quả',
        'canh', 'súp', 'tráng miệng', 'salad', 'chuẩn', 'cháo', 'bún',
        'phở', 'mì gói', 'xôi', 'dùng', 'ăn', 'món', 'buổi'
    ]
    
    @classmethod
    def classify(cls, name: str, nutrition_data: Dict[str, Any] = None) -> Literal['ingredient', 'food', 'unknown']:
        """
        Phân loại dựa trên:
        1. Keyword matching
        2. Nutritional profile
        
        Args:
            name: Tên item (ví dụ: "muối", "cơm trắng")
            nutrition_data: Dict chứa nutrition info
                {
                    'calories': float,
                    'protein': float,
                    'carbs': float,
                    'fat': float,
                    'fiber': float,
                    'vitamin_a': float,
                    'vitamin_c': float,
                    'calcium': float,
                    'iron': float,
                }
        
        Returns:
            'ingredient' | 'food' | 'unknown'
        """
        # Rule 1: Keyword matching (dễ nhất)
        keyword_result = cls._check_keywords(name)
        if keyword_result:
            return keyword_result
        
        # Rule 2: Nutritional profile
        if nutrition_data:
            nutrition_result = cls._check_nutrition(nutrition_data)
            if nutrition_result:
                return nutrition_result
        
        return 'unknown'
    
    @classmethod
    def _check_keywords(cls, name: str) -> Literal['ingredient', 'food', None]:
        """Kiểm tra từ khóa"""
        name_lower = name.lower().strip()
        
        # Check ingredient keywords
        for keyword in cls.INGREDIENT_KEYWORDS:
            if keyword in name_lower:
                return 'ingredient'
        
        # Check food keywords
        for keyword in cls.FOOD_KEYWORDS:
            if keyword in name_lower:
                return 'food'
        
        return None
    
    @classmethod
    def _check_nutrition(cls, nutrition_data: Dict) -> Literal['ingredient', 'food', None]:
        """
        Phân loại dựa trên dinh dưỡng:
        
        INGREDIENT: 
          - calories = 0 hoặc None
          - Có vitamins/minerals/fiber
        
        FOOD:
          - calories > 0
          - Có macros (protein, carbs, fat)
        """
        calories = nutrition_data.get('calories')
        protein = nutrition_data.get('protein')
        carbs = nutrition_data.get('carbs')
        fat = nutrition_data.get('fat')
        
        # Nếu không có calories
        has_calories = calories and float(calories) > 0
        has_macros = (protein and float(protein) > 0) or \
                     (carbs and float(carbs) > 0) or \
                     (fat and float(fat) > 0)
        
        # Ingredient: KHÔNG có calories và macros
        if not has_calories and not has_macros:
            # Kiểm tra có vitamins/minerals không
            has_micronutrients = (
                nutrition_data.get('vitamin_a') or 
                nutrition_data.get('vitamin_c') or
                nutrition_data.get('calcium') or
                nutrition_data.get('iron')
            )
            if has_micronutrients:
                return 'ingredient'
        
        # Food: CÓ calories AND macros
        if has_calories and has_macros:
            return 'food'
        
        return None
    
    @classmethod
    def get_confidence_score(cls, name: str, nutrition_data: Dict = None) -> Dict[str, float]:
        """
        Tính confidence score cho mỗi category
        
        Returns:
            {
                'ingredient': 0.0-1.0,
                'food': 0.0-1.0,
                'unknown': 0.0-1.0
            }
        """
        scores = {
            'ingredient': 0.0,
            'food': 0.0,
            'unknown': 0.0
        }
        
        # Rule 1: Keyword matching (50% weight)
        keyword_result = cls._check_keywords(name)
        if keyword_result:
            scores[keyword_result] += 0.5
        
        # Rule 2: Nutrition matching (50% weight)
        if nutrition_data:
            nutrition_result = cls._check_nutrition(nutrition_data)
            if nutrition_result:
                scores[nutrition_result] += 0.5
            else:
                scores['unknown'] += 0.5
        else:
            scores['unknown'] += 0.25
        
        # Normalize
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}
        
        return scores


class NutritionDataValidator:
    """Validate nutrition data hoàn thiện"""
    
    # Typical ranges for nutrients (per 100g)
    TYPICAL_RANGES = {
        'calories': (0, 1000),           # Very high calorie items like oil
        'protein': (0, 100),             # Per 100g
        'carbs': (0, 100),
        'fat': (0, 100),
        'fiber': (0, 50),
        'sodium': (0, 5000),             # mg per 100g
        'sugar': (0, 100),
        'cholesterol': (0, 1000),        # mg per 100g
        'vitamin_a': (0, 10000),         # IU per 100g
        'vitamin_c': (0, 2000),          # mg per 100g
        'calcium': (0, 2000),            # mg per 100g
        'iron': (0, 100),                # mg per 100g
    }
    
    @classmethod
    def is_valid(cls, nutrition_data: Dict) -> bool:
        """Kiểm tra nutrition data có valid không"""
        for key, (min_val, max_val) in cls.TYPICAL_RANGES.items():
            if key in nutrition_data:
                val = float(nutrition_data[key]) if nutrition_data[key] else 0
                if not (min_val <= val <= max_val):
                    return False
        return True
    
    @classmethod
    def get_missing_fields(cls, nutrition_data: Dict) -> list:
        """Lấy danh sách cột dinh dưỡng bị thiếu"""
        return [k for k in cls.TYPICAL_RANGES.keys() if k not in nutrition_data or not nutrition_data.get(k)]
    
    @classmethod
    def estimate_from_macros(cls, calories: float, protein: float, carbs: float, fat: float) -> Dict:
        """
        Validate macros tính từ calories
        Macros sum = 4*protein + 4*carbs + 9*fat (approx)
        """
        estimated_calories = 4 * protein + 4 * carbs + 9 * fat
        
        # Nếu calories không match, có vấn đề
        if abs(estimated_calories - calories) > calories * 0.1:  # 10% tolerance
            return {
                'is_valid': False,
                'message': f'Calories mismatch: {calories} vs estimated {estimated_calories}',
                'estimated_calories': estimated_calories
            }
        
        return {'is_valid': True}
