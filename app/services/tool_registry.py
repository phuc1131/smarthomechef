"""Tool registry for LLM function calling."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from django.db.models import Q

logger = logging.getLogger(__name__)

try:
    from apps.nutrition.models import Food
except Exception:
    Food = None

try:
    from apps.nutrition.models import Recipe
except Exception:
    Recipe = None

try:
    from apps.users.models import UserProfile
except Exception:
    UserProfile = None

try:
    from apps.meal_plans.models import MealPlan
except Exception:
    MealPlan = None

def get_tools_schema():
    return [
        {
            "functionDeclarations": [
                {
                    "name": "search_food",
                    "description": "Tim kiem mon an trong co so du lieu noi bo theo ten hoac tu khoa.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Ten mon an hoac tu khoa"},
                        },
                        "required": ["query"],
                    },
                },
                {
                    "name": "search_recipe",
                    "description": "Tìm công thức nấu ăn chi tiết theo tên món ăn hoặc theo nguyên liệu đầu vào.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Tên món ăn hoặc nguyên liệu cần tìm công thức",
                            },
                        },
                        "required": ["query"],
                    },
                },
                {
                    "name": "get_food_nutrition",
                    "description": "Lay thong tin dinh duong chi tiet cua 1 mon an.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "food_name": {"type": "string", "description": "Ten mon an"},
                        },
                        "required": ["food_name"],
                    },
                },
                {
                    "name": "get_user_health_profile",
                    "description": "Lay thong tin ho so suc khoe nguoi dung.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "fields": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": [],
                    },
                },
                {
                    "name": "get_recent_nutrition_logs",
                    "description": "Lay lich su an uong gan day cua nguoi dung.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "days": {"type": "integer", "description": "So ngay gan day (1-30)"},
                        },
                        "required": [],
                    },
                },
            ]
        }
    ]

def execute_tool(tool_name, arguments, account=None):
    """Execute a tool call and return the result."""
    try:
        if tool_name == 'search_food':
            q = (arguments.get('query') or '').strip()
            if not q:
                return {'error': 'Thieu tham so query'}
            limit = int(arguments.get('limit') or 5)
            limit = max(1, min(limit, 20))
            qs = Food.objects.filter(name__icontains=q).order_by('name')[:limit]
            return {
                'results': [
                    {
                        'id': f.id,
                        'name': f.name,
                        'calories': float(f.calories or 0),
                        'protein': float(f.protein or 0),
                        'carbs': float(f.carbs or 0),
                        'fat': float(f.fat or 0),
                        'fiber': float(f.fiber or 0),
                    }
                    for f in qs
                ],
                'count': len(qs),
                'tool': tool_name,
            }
        if tool_name == 'search_recipe':
            q = (arguments.get('query') or '').strip()
            if not q:
                return {'error': 'Thieu tham so query'}
            limit = int(arguments.get('limit') or 5)
            limit = max(1, min(limit, 20))
            qs = (
                Recipe.objects.filter(
                    Q(title__icontains=q)
                    | Q(summary__icontains=q)
                    | Q(food__name__icontains=q)
                    | Q(instructions__icontains=q)
                )
                .select_related('food')
                .order_by('-created_at', 'title')[:limit]
            )
            return {
                'results': [
                    {
                        'id': r.id,
                        'title': r.title,
                        'food_name': getattr(r.food, 'name', None),
                        'summary': r.summary,
                        'instructions': r.instructions,
                        'ingredients': r.ingredients_json,
                        'source_url': r.source_url,
                        'image_url': r.image_url,
                    }
                    for r in qs
                ],
                'count': len(qs),
                'tool': tool_name,
            }
        if tool_name == 'get_food_nutrition':
            name = (arguments.get('food_name') or '').strip()
            if not name:
                return {'error': 'Thieu tham so food_name'}
            f = Food.objects.filter(name__icontains=name).order_by('name').first()
            if not f:
                return {'error': f"Khong tim thay mon an '{name}'", 'tool': tool_name}
            return {
                'food': {
                    'id': f.id,
                    'name': f.name,
                    'calories': float(f.calories or 0),
                    'protein': float(f.protein or 0),
                    'carbs': float(f.carbs or 0),
                    'fat': float(f.fat or 0),
                    'fiber': float(f.fiber or 0),
                    'sugar': getattr(f, 'sugar', None),
                    'sodium': getattr(f, 'sodium', None),
                },
                'tool': tool_name,
            }
        if tool_name == 'get_user_health_profile':
            if not account:
                return {'error': 'Khong co thong tin nguoi dung', 'tool': tool_name}
            profile = UserProfile.objects.filter(account=account).first()
            return {
                'profile': {
                    'name': getattr(profile, 'name', None),
                    'age': getattr(profile, 'age', None),
                    'height': float(getattr(profile, 'height', 0) or 0),
                    'weight': float(getattr(profile, 'weight', 0) or 0),
                    'bmi': float(getattr(profile, 'bmi', 0) or 0),
                    'health_goal': getattr(profile, 'health_goal', None),
                    'medical_conditions': getattr(profile, 'medical_conditions', None),
                    'dietary_preferences': getattr(profile, 'dietary_preferences', None),
                }
                if profile
                else None,
                'tool': tool_name,
            }
        if tool_name == 'get_recent_nutrition_logs':
            if not account:
                return {'error': 'Khong co thong tin nguoi dung', 'tool': tool_name}
            days = int(arguments.get('days') or 7)
            days = max(1, min(days, 30))
            logs = MealPlan.objects.filter(account=account).order_by('-date')[:days * 3]
            unique = []
            seen = set()
            for log in logs:
                key = (str(log.date), log.meal_type, log.food_id)
                if key in seen:
                    continue
                seen.add(key)
                unique.append({
                    'date': str(log.date),
                    'meal_type': log.meal_type,
                    'food_name': getattr(getattr(log, 'food', None), 'name', None),
                })
            return {'logs': unique[:days], 'days': days, 'tool': tool_name}
        return {'error': f"Khong biet cong cu '{tool_name}'", 'tool': tool_name}
    except Exception as exc:
        logger.exception('Tool execution failed: %s', exc)
        return {'error': str(exc), 'tool': tool_name}
