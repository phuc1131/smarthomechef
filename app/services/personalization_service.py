"""Internal personalization helpers for the AI system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from django.db.models import Avg

from apps.core_models.models import AIRecommendation, SearchEvent
from apps.nutrition.models import Food, NutritionLog
from apps.users.models import UserDisease, UserGoal, UserPreferenceProfile, UserProfile, UserFeedback


@dataclass(frozen=True)
class PersonalizedScore:
    food_id: int
    score: float
    reasons: List[str]


def build_user_preference_profile(account):
    if not account:
        return None
    profile, _ = UserPreferenceProfile.objects.get_or_create(account=account)
    return profile


def get_personalization_context(account) -> Dict[str, Any]:
    profile = UserProfile.objects.filter(account=account).first() if account else None
    preference_profile = build_user_preference_profile(account)
    goals = list(UserGoal.objects.filter(account=account)) if account else []
    diseases = list(UserDisease.objects.filter(account=account).select_related('disease')) if account else []
    recent_logs = list(
        NutritionLog.objects.filter(account=account).select_related('food').order_by('-date')[:14]
    ) if account else []

    return {
        'profile': profile,
        'preference_profile': preference_profile,
        'goals': goals,
        'diseases': diseases,
        'recent_food_ids': [log.food_id for log in recent_logs if log.food_id],
        'recent_logs': recent_logs,
    }


def _normalize_tokens(value: Optional[Iterable[str]]) -> List[str]:
    return [str(item).strip().lower() for item in value or [] if str(item).strip()]


def score_food_for_user(account, food: Food) -> PersonalizedScore:
    context = get_personalization_context(account)
    reasons: List[str] = []
    score = 0.5

    profile = context.get('profile')
    preference_profile = context.get('preference_profile')
    goals = context.get('goals') or []
    diseases = context.get('diseases') or []
    recent_food_ids = set(context.get('recent_food_ids') or [])

    food_name = (getattr(food, 'name', '') or '').lower()
    category_name = ''
    if getattr(food, 'category', None) and getattr(food.category, 'name', None):
        category_name = food.category.name.lower()
    elif getattr(food, 'category_name', None):
        category_name = str(food.category_name).lower()

    if food.id in recent_food_ids:
        score -= 0.12
        reasons.append('Đã ăn gần đây')

    preferred_categories = _normalize_tokens(getattr(preference_profile, 'preferred_categories', None) or [])
    if preferred_categories and any(token in category_name or token in food_name for token in preferred_categories):
        score += 0.18
        reasons.append('Khớp danh mục ưa thích')

    avoided_keywords = _normalize_tokens(getattr(preference_profile, 'avoided_keywords', None) or [])
    if avoided_keywords and any(token in food_name for token in avoided_keywords):
        score -= 0.30
        reasons.append('Trùng từ khóa cần tránh')

    if goals and any(getattr(goal, 'goal_type', '') == 'weight_loss' for goal in goals):
        calories = float(getattr(food, 'total_calories', 0) or 0)
        if calories <= 300:
            score += 0.10
            reasons.append('Phù hợp giảm cân')
        elif calories >= 600:
            score -= 0.10
            reasons.append('Calories cao hơn mục tiêu giảm cân')

    disease_names = [getattr(item.disease, 'name', '').lower() for item in diseases if getattr(item, 'disease', None)]
    if any('diabetes' in item or 'tiểu đường' in item for item in disease_names):
        if getattr(food, 'is_diabetes_friendly', False):
            score += 0.15
            reasons.append('Thân thiện với tiểu đường')
        else:
            score -= 0.08

    if profile and getattr(profile, 'budget_limit', None):
        estimated_cost = getattr(food, 'estimated_cost', None)
        budget_limit = float(profile.budget_limit or 0)
        if estimated_cost is not None and float(estimated_cost) <= budget_limit:
            score += 0.08
            reasons.append('Nằm trong ngân sách')

    feedback_avg = (
        UserFeedback.objects.filter(account=account).aggregate(avg_rating=Avg('rating')).get('avg_rating')
        if account else None
    )
    if feedback_avg:
        score += min(0.08, float(feedback_avg) / 100.0)

    score = max(0.0, min(1.0, round(score, 4)))
    return PersonalizedScore(food_id=food.id, score=score, reasons=reasons)


def rank_food_candidates(account, foods: Iterable[Food], limit: int = 10) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []
    for food in foods:
        score_payload = score_food_for_user(account, food)
        ranked.append({
            'food': food,
            'score': score_payload.score,
            'reasons': score_payload.reasons,
        })

    ranked.sort(key=lambda item: item['score'], reverse=True)
    return ranked[:limit]


def log_ai_recommendation(account, food: Food, score: float, reason: str = '', model_version: str = 'internal-v1'):
    if not account or not food:
        return None
    return AIRecommendation.objects.create(
        account=account,
        food=food,
        score=score,
        reason=reason,
        stt=None,
    )


def summarize_ai_activity(account) -> Dict[str, Any]:
    if not account:
        return {
            'searches': 0,
            'recommendations': 0,
            'recent_food_logs': 0,
        }

    return {
        'searches': SearchEvent.objects.filter(account=account).count(),
        'recommendations': AIRecommendation.objects.filter(account=account).count(),
        'recent_food_logs': NutritionLog.objects.filter(account=account).count(),
    }
