"""High level AI orchestrator for the project."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from apps.chat.models import Intent
from app.config import GEMINI_ENABLED
from app.services.model_training_service import (
    get_intent_model_status,
    predict_intent,
    predict_top_intents,
    train_intent_classifier,
)
from app.services.personalization_service import (
    build_user_preference_profile,
    get_personalization_context,
    rank_food_candidates,
    score_food_for_user,
    summarize_ai_activity,
)


class AIOrchestratorService:
    """Single entrypoint for the project's internal AI layer."""

    INTENT_RULES = [
        ('meal_plan', ('thuc don', 'thực đơn', 'meal plan', 'menu', 'lập thực đơn', 'lap thuc don', 'kế hoạch ăn')),
        ('nutrition', ('dinh duong', 'dinh dưỡng', 'calo', 'calories', 'protein', 'carb', 'fat', 'nutrition')),
        ('recipe', ('công thức', 'cong thuc', 'recipe', 'cach lam', 'cách làm', 'nấu', 'xào', 'luộc', 'rim')),
        ('recommendation', ('gợi ý', 'goi y', 'recommend', 'nên ăn', 'nen an', 'món nào', 'mon nao')),
        ('shopping', ('mua sắm', 'danh sách mua', 'shopping list', 'shopping', 'cần mua', 'can mua')),
        ('ingredient', ('nguyên liệu', 'nguyen lieu', 'ingredient', 'thành phần', 'thanh phan')),
    ]

    CAPABILITIES = [
        {
            'name': 'intent_classification',
            'backend': 'internal_naive_bayes',
            'description': 'Phân loại ý định từ lịch sử chat, pattern và nhãn MessageIntent.',
        },
        {
            'name': 'personalization',
            'backend': 'db_scoring',
            'description': 'Chấm điểm món ăn theo hồ sơ, bệnh lý, sở thích và lịch sử ăn.',
        },
        {
            'name': 'chat_generation',
            'backend': 'gemini_fallback',
            'description': 'Sinh phản hồi chat bằng Gemini khi cache và dữ liệu nội bộ không đủ.',
        },
        {
            'name': 'recipe_generation',
            'backend': 'hybrid_db_plus_gemini',
            'description': 'Sinh và biến thể công thức từ nguyên liệu và dữ liệu nội bộ.',
        },
        {
            'name': 'meal_plan_generation',
            'backend': 'hybrid_db_plus_gemini',
            'description': 'Lập thực đơn dựa trên ngữ cảnh người dùng, ngân sách và bệnh lý.',
        },
    ]

    @staticmethod
    def get_capabilities() -> List[Dict[str, Any]]:
        return list(AIOrchestratorService.CAPABILITIES)

    @staticmethod
    def get_health_report() -> Dict[str, Any]:
        return {
            'gemini_enabled': GEMINI_ENABLED,
            'intent_model': get_intent_model_status(),
            'capabilities': AIOrchestratorService.get_capabilities(),
        }

    @staticmethod
    def ensure_training_snapshot(force: bool = False) -> Dict[str, Any]:
        return train_intent_classifier(force=force)

    @staticmethod
    def _resolve_intent_record(intent_name: Optional[str]):
        if not intent_name:
            return None
        return Intent.objects.filter(name__iexact=intent_name).first()

    @staticmethod
    def _keyword_fallback(user_text: str):
        text = (user_text or '').lower()
        for canonical_name, keywords in AIOrchestratorService.INTENT_RULES:
            if any(keyword in text for keyword in keywords):
                return AIOrchestratorService._resolve_intent_record(canonical_name)
        return None

    @staticmethod
    def classify_intent(user_text: str) -> Tuple[Optional[Any], float]:
        prediction = predict_intent(user_text)
        if prediction.intent_name:
            intent = AIOrchestratorService._resolve_intent_record(prediction.intent_name)
            if intent:
                return intent, prediction.confidence

        fallback_intent = AIOrchestratorService._keyword_fallback(user_text)
        if fallback_intent:
            return fallback_intent, 0.6

        return None, 0.0

    @staticmethod
    def classify_intent_details(user_text: str) -> Dict[str, Any]:
        prediction = predict_intent(user_text)
        return {
            'top_intents': predict_top_intents(user_text),
            'prediction': prediction,
        }

    @staticmethod
    def get_personalization_summary(account) -> Dict[str, Any]:
        context = get_personalization_context(account)
        return {
            'has_profile': context.get('profile') is not None,
            'goal_count': len(context.get('goals') or []),
            'disease_count': len(context.get('diseases') or []),
            'recent_food_count': len(context.get('recent_food_ids') or []),
            'activity': summarize_ai_activity(account),
        }


__all__ = [
    'AIOrchestratorService',
    'build_user_preference_profile',
    'get_personalization_context',
    'rank_food_candidates',
    'score_food_for_user',
    'summarize_ai_activity',
]
