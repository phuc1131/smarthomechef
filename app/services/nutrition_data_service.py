"""
Spoonacular API Service - Lấp dữ liệu dinh dưỡng từ API

Tấtcả các cột trống trong bảng Food/FoodDetail sẽ được pull từ Spoonacular API
"""

import requests
import json
import re
import hashlib
from decimal import Decimal
from typing import Dict, Optional, Any
from django.core.cache import cache
from django.db import models

from app.config import SPOONACULAR_API_KEY, SPOONACULAR_BASE_URL
import unicodedata
from apps.nutrition.models import Food, Ingredient, IngredientNutrition
from app.services.food_classifier_service import FoodClassifier, NutritionDataValidator
from app.services.external_apis import _gemini_generate_text, AI_AVAILABLE
from app.config import GEMINI_RETRIES
import time


class SpoonacularService:
    """Lấy dữ liệu từ Spoonacular API"""
    
    BASE_URL = SPOONACULAR_BASE_URL or "https://api.spoonacular.com"
    API_KEY = SPOONACULAR_API_KEY
    
    # Endpoints
    INGREDIENT_SEARCH_URL = f"{BASE_URL}/food/ingredients/search"
    INGREDIENT_INFO_URL = f"{BASE_URL}/food/ingredients/{{id}}/information"
    
    # Cache duration (24 hours)
    CACHE_TTL = 86400

    @staticmethod
    def _cache_suffix(value: str) -> str:
        raw = (value or '').strip().lower()
        return hashlib.sha1(raw.encode('utf-8')).hexdigest()
    
    @classmethod
    def search_ingredient(cls, ingredient_name: str, number: int = 5) -> list:
        """Tìm kiếm nguyên liệu từ Spoonacular"""
        if not cls.API_KEY:
            return []
        
        cache_key = f"spoonacular_search_{cls._cache_suffix(ingredient_name)}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        try:
            params = {
                'query': ingredient_name,
                'number': number,
                'apiKey': cls.API_KEY,
                'language': 'en'  # Spoonacular tốt nhất với English
            }
            
            response = requests.get(cls.INGREDIENT_SEARCH_URL, params=params, timeout=5)
            if response.status_code == 200:
                payload = response.json()
                if isinstance(payload, list):
                    results = payload
                elif isinstance(payload, dict):
                    results = payload.get('results') or payload.get('items') or []
                else:
                    results = []
                cache.set(cache_key, results, cls.CACHE_TTL)
                return results
        except Exception as e:
            print(f"Error searching ingredient: {e}")
        
        return []
    
    @classmethod
    def get_ingredient_info(cls, ingredient_id: int) -> Optional[Dict]:
        """Lấy thông tin chi tiết nguyên liệu"""
        if not cls.API_KEY:
            return None
        
        cache_key = f"spoonacular_ingredient_{ingredient_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        try:
            url = cls.INGREDIENT_INFO_URL.format(id=ingredient_id)
            params = {
                'apiKey': cls.API_KEY,
                'amount': 100,  # Per 100g
                'unit': 'g'
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                cache.set(cache_key, data, cls.CACHE_TTL)
                return data
        except Exception as e:
            print(f"Error getting ingredient info: {e}")
        
        return None
    
    @classmethod
    def extract_nutrition_data(cls, api_data: Dict) -> Dict[str, Any]:
        """Extract nutrition data từ Spoonacular response"""
        nutrition = {
            'calories': 0,
            'protein': 0,
            'carbs': 0,
            'fat': 0,
            'fiber': 0,
            'sodium': 0,
            'sugar': 0,
            'cholesterol': 0,
            'vitamin_a': 0,
            'vitamin_c': 0,
            'calcium': 0,
            'iron': 0,
        }
        
        # Spoonacular uses 'nutrition' key
        if 'nutrition' in api_data:
            nut = api_data['nutrition']
            
            # Macros (in grams)
            if 'nutrients' in nut:
                nutrients_map = {
                    'Calories': 'calories',
                    'Protein': 'protein',
                    'Carbohydrates': 'carbs',
                    'Fat': 'fat',
                    'Fiber': 'fiber',
                    'Sodium': 'sodium',
                    'Sugar': 'sugar',
                    'Cholesterol': 'cholesterol',
                    'Vitamin A': 'vitamin_a',
                    'Vitamin C': 'vitamin_c',
                    'Calcium': 'calcium',
                    'Iron': 'iron',
                }
                
                for nutrient in nut['nutrients']:
                    name = nutrient.get('name', '')
                    value = nutrient.get('amount', 0)
                    
                    for api_name, field_name in nutrients_map.items():
                        if api_name.lower() in name.lower():
                            nutrition[field_name] = float(value)
                            break
        
        return nutrition
    
    @classmethod
    def fill_food_nutrition(cls, food_id: int, ingredient_api_id: int) -> bool:
        """
        Lấp dữ liệu dinh dưỡng cho Food từ Spoonacular
        """
        try:
            food = Food.objects.get(id=food_id)
            
            # Get data từ API
            api_data = cls.get_ingredient_info(ingredient_api_id)
            if not api_data:
                return False
            
            nutrition = cls.extract_nutrition_data(api_data)
            
            # Update Food model (macros)
            food.calories = Decimal(str(nutrition['calories']))
            food.protein = Decimal(str(nutrition['protein']))
            food.carbs = Decimal(str(nutrition['carbs']))
            food.fat = Decimal(str(nutrition['fat']))
            food.save()
            
            # Update Food model (micronutrients consolidated on Food)
            food.fiber = Decimal(str(nutrition['fiber']))
            food.sodium = nutrition['sodium']
            food.sugar = nutrition['sugar']
            food.cholesterol = nutrition['cholesterol']
            food.vitamin_a = nutrition['vitamin_a']
            food.vitamin_c = nutrition['vitamin_c']
            food.calcium = nutrition['calcium']
            food.iron = nutrition['iron']
            food.save()
            
            return True
        except Exception as e:
            print(f"Error filling food nutrition: {e}")
            return False


class LocalNutritionDatabase:
    """Database địa phương cho ingredient & food"""
    
    # Vietnamese common ingredients và nutrition (per 100g)
    INGREDIENT_DATA = {
        'sữa': {
            'type': 'ingredient',
            'calories': 60,
            'protein': 3.3,
            'carbs': 5,
            'fat': 3.25,
            'fiber': 0,
            'sodium': 44,
            'vitamin_a': 50,
            'vitamin_c': 0,
            'calcium': 120,
            'iron': 0.1,
        },
        'sữa tươi': {
            'type': 'ingredient',
            'calories': 64,
            'protein': 3.4,
            'carbs': 4.8,
            'fat': 3.6,
            'fiber': 0,
            'sodium': 44,
            'vitamin_a': 50,
            'vitamin_c': 0,
            'calcium': 125,
            'iron': 0.03,
        },
        'sữa đậu nành': {
            'type': 'ingredient',
            'calories': 33,
            'protein': 1.6,
            'carbs': 2.6,
            'fat': 1.9,
            'fiber': 0.3,
            'sodium': 50,
            'vitamin_a': 0,
            'vitamin_c': 0,
            'calcium': 25,
            'iron': 0.2,
        },
        'muối': {
            'type': 'ingredient',
            'calories': 0,
            'protein': 0,
            'carbs': 0,
            'fat': 0,
            'fiber': 0,
            'sodium': 38758,  # Very high!
            'vitamin_a': 0,
            'vitamin_c': 0,
            'calcium': 1040,
            'iron': 0.28,
        },
        'đường': {
            'type': 'ingredient',
            'calories': 0,
            'protein': 0,
            'carbs': 100,  # Pure carbs
            'fat': 0,
            'fiber': 0,
            'sodium': 2,
            'sugar': 100,
            'vitamin_a': 0,
            'vitamin_c': 0,
            'calcium': 0,
            'iron': 0,
        },
        'dầu ăn': {
            'type': 'ingredient',
            'calories': 884,
            'protein': 0,
            'carbs': 0,
            'fat': 100,
            'fiber': 0,
            'sodium': 0,
            'vitamin_a': 0,
            'vitamin_c': 0,
            'calcium': 0,
            'iron': 0,
        },
        'nước mắm': {
            'type': 'ingredient',
            'calories': 0,
            'protein': 24,
            'carbs': 0,
            'fat': 0,
            'fiber': 0,
            'sodium': 7800,
            'vitamin_a': 0,
            'vitamin_c': 0,
            'calcium': 150,
            'iron': 0,
        },
    }
    
    # Vietnamese common foods
    FOOD_DATA = {
        'cơm trắng': {
            'type': 'food',
            'category': 'Cơm & Mì',
            'calories': 130,
            'protein': 2.7,
            'carbs': 28,
            'fat': 0.3,
            'fiber': 0.4,
            'sodium': 2,
            'sugar': 0.1,
            'vitamin_a': 0,
            'vitamin_c': 0,
            'calcium': 10,
            'iron': 0.8,
        },
        'mì': {
            'type': 'food',
            'category': 'Cơm & Mì',
            'calories': 138,
            'protein': 3.5,
            'carbs': 30,
            'fat': 0.4,
            'fiber': 1,
            'sodium': 80,
            'sugar': 0.5,
            'vitamin_a': 0,
            'vitamin_c': 0,
            'calcium': 7,
            'iron': 1.5,
        },
        'rau xanh': {
            'type': 'food',
            'category': 'Rau & Quả',
            'calories': 23,
            'protein': 2.6,
            'carbs': 3.6,
            'fat': 0.4,
            'fiber': 2.4,
            'sodium': 65,
            'sugar': 0.4,
            'vitamin_a': 7000,
            'vitamin_c': 100,
            'calcium': 250,
            'iron': 2.7,
        },
        'thịt gà': {
            'type': 'food',
            'category': 'Thịt & Cá',
            'calories': 165,
            'protein': 31,
            'carbs': 0,
            'fat': 3.6,
            'fiber': 0,
            'sodium': 75,
            'sugar': 0,
            'vitamin_a': 6,
            'vitamin_c': 0,
            'calcium': 11,
            'iron': 0.8,
        },
        'cá': {
            'type': 'food',
            'category': 'Thịt & Cá',
            'calories': 100,
            'protein': 20,
            'carbs': 0,
            'fat': 1.2,
            'fiber': 0,
            'sodium': 80,
            'sugar': 0,
            'vitamin_a': 60,
            'vitamin_c': 0,
            'calcium': 15,
            'iron': 0.5,
        },
        'trứng': {
            'type': 'food',
            'category': 'Sữa & Trứng',
            'calories': 155,
            'protein': 13,
            'carbs': 1.1,
            'fat': 11,
            'fiber': 0,
            'sodium': 124,
            'sugar': 1.1,
            'vitamin_a': 495,
            'vitamin_c': 0,
            'calcium': 56,
            'iron': 1.8,
        },
    }
    
    @classmethod
    def get_nutrition_data(cls, name: str) -> Optional[Dict]:
        """Lấy nutrition data từ local database"""
        if not isinstance(name, str):
            return None
        name_lower = name.lower().strip()
        # normalized ASCII (no diacritics) for more robust matching
        name_ascii = unicodedata.normalize('NFKD', name_lower).encode('ascii', 'ignore').decode('ascii')
        
        # Search in ingredients
        for key, data in cls.INGREDIENT_DATA.items():
            k = key.lower()
            k_ascii = unicodedata.normalize('NFKD', k).encode('ascii', 'ignore').decode('ascii')
            if k in name_lower or name_lower in k or k_ascii in name_ascii or name_ascii in k_ascii:
                return data.copy()
        
        # Search in foods
        for key, data in cls.FOOD_DATA.items():
            k = key.lower()
            k_ascii = unicodedata.normalize('NFKD', k).encode('ascii', 'ignore').decode('ascii')
            if k in name_lower or name_lower in k or k_ascii in name_ascii or name_ascii in k_ascii:
                return data.copy()
        
        return None


class NutritionDataFiller:
    """Fill lấp dữ liệu trống cho Food model"""

    @staticmethod
    def _extract_json_payload(text: str) -> Optional[Dict]:
        if not text:
            return None

        raw = str(text).strip()
        if raw.startswith('```'):
            lines = raw.splitlines()
            if lines and lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].startswith('```'):
                lines = lines[:-1]
            raw = '\n'.join(lines).strip()

        start_idx = raw.find('{')
        end_idx = raw.rfind('}')
        if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
            return None

        candidate = raw[start_idx:end_idx + 1]
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    
    @classmethod
    def fill_missing_nutrition(cls, food: Food, use_spoonacular: bool = True, use_gemini: bool = True) -> bool:
        """
        Lấp dữ liệu trống cho một Food
        
        Strategy:
        1. Kiểm tra local database
        2. Nếu không có, dùng Spoonacular API
        3. Classify nó
        """
        # Try local database first
        local_data = LocalNutritionDatabase.get_nutrition_data(food.name)
        if local_data:
            cls._apply_nutrition_data(food, local_data)
            return True
        
        # Try Spoonacular
        if use_spoonacular:
            search_results = SpoonacularService.search_ingredient(food.name, number=1)
            if search_results:
                ingredient_id = search_results[0].get('id')
                if ingredient_id:
                    return SpoonacularService.fill_food_nutrition(food.id, ingredient_id)

        if use_gemini and AI_AVAILABLE:
            prompt = (
                'Bạn là chuyên gia dinh dưỡng. Hãy ước tính thông tin dinh dưỡng cho món sau theo 100g. '
                'Chỉ trả về JSON hợp lệ với các khóa calories, protein, carbs, fat, fiber, sodium, sugar, cholesterol, vitamin_a, vitamin_c, calcium, iron.\n\n'
                f'Tên món: {food.name}\n'
                f'Mô tả: {food.description or "không có"}\n'
                'Nếu không chắc chắn, hãy đưa ra giá trị hợp lý theo dữ liệu dinh dưỡng phổ biến, không giải thích thêm.'
            )
            last_exc = None
            for attempt in range(1, max(1, GEMINI_RETRIES) + 1):
                try:
                    gemini_text = _gemini_generate_text(
                        prompt,
                        system_instruction='Ban la chuyen gia dinh duong. Chi tra ve JSON hop le.',
                        max_output_tokens=512,
                    )
                    payload = cls._extract_json_payload(gemini_text)
                    if payload:
                        cls._apply_nutrition_data(food, payload)
                        return True
                    break
                except Exception as exc:
                    last_exc = exc
                    # If rate-limited, wait a bit before retrying
                    if attempt < GEMINI_RETRIES:
                        wait = attempt * 5
                        time.sleep(wait)
            # give up after retries
            if last_exc:
                print(f'Gemini fill_food_nutrition failed for {food.id}: {last_exc}')
        
        return False

    @classmethod
    def _apply_ingredient_nutrition_data(cls, ingredient: Ingredient, nutrition_data: Dict):
        ingredient_nutrition, _ = IngredientNutrition.objects.update_or_create(
            ingredient=ingredient,
            defaults={
                'calories': Decimal(str(nutrition_data.get('calories', 0) or 0)),
                'protein': Decimal(str(nutrition_data.get('protein', 0) or 0)),
                'carbs': Decimal(str(nutrition_data.get('carbs', 0) or 0)),
                'fat': Decimal(str(nutrition_data.get('fat', 0) or 0)),
                'fiber': Decimal(str(nutrition_data.get('fiber', 0) or 0)),
            }
        )
        return ingredient_nutrition

    @classmethod
    def fill_missing_ingredient_nutrition(
        cls,
        ingredient: Ingredient,
        use_spoonacular: bool = True,
        use_gemini: bool = True,
    ) -> bool:
        """Fill nutrition per 100g cho Ingredient, ưu tiên local -> Spoonacular -> Gemini."""
        local_data = LocalNutritionDatabase.get_nutrition_data(ingredient.name)
        if local_data:
            cls._apply_ingredient_nutrition_data(ingredient, local_data)
            return True

        if use_spoonacular:
            search_results = SpoonacularService.search_ingredient(ingredient.name, number=1)
            if search_results:
                ingredient_id = search_results[0].get('id')
                if ingredient_id:
                    api_data = SpoonacularService.get_ingredient_info(ingredient_id)
                    if api_data:
                        nutrition = SpoonacularService.extract_nutrition_data(api_data)
                        cls._apply_ingredient_nutrition_data(ingredient, nutrition)
                        return True

        if use_gemini and AI_AVAILABLE:
                prompt = (
                    'Bạn là chuyên gia dinh dưỡng. Hãy ước tính dinh dưỡng cho nguyên liệu sau theo 100g. '\
                    'Chỉ trả về JSON hợp lệ với các khóa calories, protein, carbs, fat, fiber.\n\n'
                    f'Nguyên liệu: {ingredient.name}\n'
                    'Nếu có mô tả hoặc tên tiếng Việt mơ hồ, vẫn hãy suy luận theo nguyên liệu phổ biến tương ứng.'
                )
                last_exc = None
                for attempt in range(1, max(1, GEMINI_RETRIES) + 1):
                    try:
                        gemini_text = _gemini_generate_text(
                            prompt,
                            system_instruction='Ban la chuyen gia dinh duong. Chi tra ve JSON hop le.',
                            max_output_tokens=512,
                        )
                        payload = cls._extract_json_payload(gemini_text)
                        if payload:
                            cls._apply_ingredient_nutrition_data(ingredient, payload)
                            return True
                        break
                    except Exception as exc:
                        last_exc = exc
                        if attempt < GEMINI_RETRIES:
                            wait = attempt * 5
                            time.sleep(wait)
                if last_exc:
                    print(f'Gemini fill_missing_ingredient_nutrition failed for {ingredient.id}: {last_exc}')

        return False
    
    @classmethod
    def _apply_nutrition_data(cls, food: Food, nutrition_data: Dict):
        """Apply nutrition data to Food."""
        # Update Food (macros)
        if 'calories' in nutrition_data:
            food.calories = Decimal(str(nutrition_data['calories']))
        if 'protein' in nutrition_data:
            food.protein = Decimal(str(nutrition_data['protein']))
        if 'carbs' in nutrition_data:
            food.carbs = Decimal(str(nutrition_data['carbs']))
        if 'fat' in nutrition_data:
            food.fat = Decimal(str(nutrition_data['fat']))
        
        food.save()
        
        for field in ['fiber', 'sodium', 'sugar', 'cholesterol', 'vitamin_a', 'vitamin_c', 'calcium', 'iron']:
            if field in nutrition_data:
                setattr(food, field, nutrition_data[field])

        food.save()
    
    @classmethod
    def fill_all_foods(cls, batch_size: int = 10) -> Dict:
        """Fill nutrition data cho tất cả Foods có cột trống"""
        stats = {
            'total': 0,
            'filled': 0,
            'skipped': 0,
            'failed': 0,
        }
        
        # Tìm tất cả foods có cột trống
        foods_with_missing = Food.objects.filter(
            models.Q(calories__isnull=True) | 
            models.Q(protein__isnull=True) |
            models.Q(carbs__isnull=True) |
            models.Q(fat__isnull=True)
        )[:batch_size]
        
        for food in foods_with_missing:
            stats['total'] += 1
            
            try:
                if cls.fill_missing_nutrition(food):
                    stats['filled'] += 1
                else:
                    stats['failed'] += 1
            except Exception as e:
                print(f"Error filling {food.name}: {e}")
                stats['failed'] += 1
        
        return stats
