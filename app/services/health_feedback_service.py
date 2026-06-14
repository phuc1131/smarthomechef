from typing import Any, Dict, Optional

from apps.chat.models import ChatMessage, Intent, IntentEmbedding, MessageIntent, Pattern
from apps.core_models.ai_learning_models import UserFeedbackFood, UserFeedbackRecommendation
from app.services.semantic_intent_service import build_text_embedding_vector
from app.services.model_training_service import train_intent_classifier


def append_health_feedback(response_text: str, account: Any = None, user_text: Optional[str] = None) -> str:
    if response_text is None:
        response_text = ''
    return response_text


def build_health_feedback(account: Any = None, user_text: Optional[str] = None) -> Dict[str, Any]:
    return {
        'message': '',
        'user_text': user_text or '',
        'account_id': getattr(account, 'id', None),
    }


def _extract_learning_texts(limit: int = 500):
    texts = []
    try:
        for item in MessageIntent.objects.select_related('message', 'intent').order_by('-id')[:limit]:
            if item.message and item.intent and item.message.content:
                texts.append((item.intent.name, item.message.content))
    except Exception:
        pass
    return texts


def refresh_chat_learning_from_history(limit: int = 500) -> Dict[str, Any]:
    learned = 0
    for intent_name, text in _extract_learning_texts(limit=limit):
        if not intent_name or not text:
            continue
        intent = Intent.objects.filter(name__iexact=intent_name).first()
        if not intent:
            continue
        try:
            Pattern.objects.get_or_create(intent=intent, text=text.strip())
            IntentEmbedding.objects.update_or_create(
                intent_name=intent.name,
                message=None,
                pattern=Pattern.objects.filter(intent=intent, text=text.strip()).first(),
                defaults={
                    'embedding_vector': build_text_embedding_vector(text),
                    'source_type': 'pattern',
                    'confidence': 0.9,
                },
            )
            learned += 1
        except Exception:
            continue

    snapshot = train_intent_classifier(force=True)
    return {
        'learned_examples': learned,
        'trained_documents': snapshot.get('document_count', 0),
        'intent_count': snapshot.get('intent_count', 0),
        'version': snapshot.get('version'),
    }


def refresh_learning_from_feedback(limit: int = 500) -> Dict[str, Any]:
    food_feedbacks = 0
    recommendation_feedbacks = 0

    try:
        for fb in UserFeedbackRecommendation.objects.order_by('-created_at')[:limit]:
            recommendation_feedbacks += 1
            intent = Intent.objects.filter(name__iexact='recommendation').first()
            if not intent:
                continue
            example_text = ''
            if fb.context and isinstance(fb.context, dict):
                example_text = str(fb.context.get('user_text') or fb.context.get('query') or '').strip()
            if not example_text:
                example_text = f'gợi ý món ăn {getattr(fb.food, "name", "")}'.strip()
            if example_text:
                try:
                    pattern, _ = Pattern.objects.get_or_create(intent=intent, text=example_text)
                    IntentEmbedding.objects.update_or_create(
                        pattern=pattern,
                        defaults={
                            'intent_name': intent.name,
                            'embedding_vector': build_text_embedding_vector(example_text),
                            'source_type': 'pattern',
                            'confidence': 0.85 if fb.was_accepted or fb.was_helpful else 0.55,
                        },
                    )
                except Exception:
                    pass
    except Exception:
        pass

    try:
        for fb in UserFeedbackFood.objects.order_by('-created_at')[:limit]:
            food_feedbacks += 1
    except Exception:
        pass

    learning = refresh_chat_learning_from_history(limit=limit)
    learning.update({
        'food_feedbacks': food_feedbacks,
        'recommendation_feedbacks': recommendation_feedbacks,
    })
    return learning
