"""High level AI orchestrator for the project."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from django.db.models import Q
from django.utils import timezone as django_timezone
from apps.chat.models import ChatResponseCache, Intent, MessageIntent, Pattern
from apps.core_models.models import SearchEvent
from apps.core_models.ai_learning_models import ModelMetadata
from app.config import GEMINI_ENABLED
from app.services.ab_testing_service import ABTestingService
from app.services.chat_text_service import normalize_chat_text
from app.services.model_training_service import (
    get_intent_model_status,
    predict_intent,
    predict_top_intents,
    train_intent_classifier,
)
from app.services.health_feedback_service import refresh_learning_from_feedback
from app.services.intent_classifier import classify_intent as local_classify_intent
from app.services.external_apis import classify_intent_with_local_llm
from app.services.personalization_service import (
    build_db_backed_candidate_pool,
    build_user_preference_profile,
    get_personalization_context,
    rank_food_candidates,
    score_food_for_user,
    semantic_search_with_scores,
    filter_food_candidates,
    summarize_ai_activity,
)
from app.services.semantic_intent_service import (
    classify_intent_by_embedding,
    get_intent_embedding_status,
)
from app.services.router_policy_service import evaluate_policies, decide_route


class AIOrchestratorService:
    """Single entrypoint for the project's internal AI layer."""

    INTENT_RULES = [
        ('greeting', ('chào', 'chao', 'hello', 'hi', 'alo', 'allo', 'hey', 'tạm biệt', 'tam biet', 'bye')),
        ('meal_plan', ('thuc don', 'thực đơn', 'meal plan', 'meal_plan', 'menu', 'lập thực đơn', 'lap thuc don', 'kế hoạch ăn', 'ăn gì cho', 'an gi cho')),
        ('nutrition', ('dinh duong', 'dinh dưỡng', 'calo', 'calories', 'protein', 'carb', 'fat', 'nutrition', 'thành phần dinh dưỡng')),
        ('recipe', ('công thức', 'cong thuc', 'recipe', 'cach lam', 'cách làm', 'nấu', 'xào', 'luộc', 'rim', 'hướng dẫn nấu')),
        ('recommendation', ('gợi ý', 'goi y', 'recommend', 'recommendation', 'nên ăn', 'nen an', 'món nào', 'mon nao', 'tìm món', 'tim mon')),
        ('shopping', ('mua sắm', 'danh sách mua', 'shopping list', 'shopping', 'can mua', 'cần mua', 'đi chợ', 'di cho')),
        ('ingredient', ('nguyên liệu', 'nguyen lieu', 'ingredient', 'thành phần', 'thanh phan')),
    ]

    CAPABILITIES = [
        {
            'name': 'intent_classification',
            'backend': 'semantic_embedding_with_fallback',
            'description': '[PHÂN LOẠI Ý ĐỊNH] Phân loại ý định từ lịch sử chat, pattern, embedding và nhãn MessageIntent. Sử dụng embedding similarity kết hợp với Naive Bayes model và keyword rules để xác định intent người dùng.',
        },
        {
            'name': 'personalization',
            'backend': 'constraint_hybrid_ranker',
            'description': '[BỘ LỌC CÁ NHÂN HÓA] Chấm điểm món ăn theo hồ sơ, bệnh lý, sở thích, ngân sách và lịch sử ăn. Áp dụng token-based matching với Vietnamese normalization để tránh duplicate recommendations.',
        },
        {
            'name': 'chat_generation',
            'backend': 'ollama_qwen_primary_gemini_fallback',
            'description': '[QUYẾT ĐỊNH ĐIỀU PHỐI] Sinh phản hồi chat: [1] Ollama/Qwen2.5:7b (primary) -> [2] Google Gemini (fallback). Lựa chọn route dựa trên intent confidence, local candidates score và status Ollama server.',
        },
        {
            'name': 'recipe_generation',
            'backend': 'ollama_qwen_primary_gemini_fallback',
            'description': 'Sinh và biến thể công thức từ nguyên liệu và dữ liệu nội bộ bằng Ollama/Qwen (primary) -> Gemini (fallback).',
        },
        {
            'name': 'meal_plan_generation',
            'backend': 'ollama_qwen_primary_gemini_fallback',
            'description': 'Lập thực đơn dựa trên ngữ cảnh người dùng, ngân sách và bệnh lý bằng Ollama/Qwen (primary) -> Gemini (fallback).',
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
            'intent_embedding': get_intent_embedding_status(),
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
        normalized = normalize_chat_text(user_text)
        for canonical_name, keywords in AIOrchestratorService.INTENT_RULES:
            if any(keyword in normalized for keyword in keywords):
                return AIOrchestratorService._resolve_intent_record(canonical_name)
        return None

    @staticmethod
    def _pattern_similarity_fallback(user_text: str, threshold: float = 0.82):
        """So khớp thông minh với các mẫu câu (Patterns) trong DB."""
        try:
            from apps.chat.models import Pattern
            from app.services.similarity_service import compute_smart_similarity
            
            # Lấy các pattern phổ biến hoặc gần đây
            patterns = Pattern.objects.all().select_related('intent')[:100]
            best_intent = None
            max_sim = 0.0
            
            for p in patterns:
                sim = compute_smart_similarity(user_text, p.text)
                if sim > max_sim:
                    max_sim = sim
                    best_intent = p.intent
            
            if best_intent and max_sim >= threshold:
                return best_intent, max_sim
        except Exception:
            pass
        return None, 0.0

    @staticmethod
    def _db_intent_signal(user_text: str) -> Tuple[Optional[Any], float, Dict[str, Any]]:
        normalized = normalize_chat_text(user_text)
        if not normalized:
            return None, 0.0, {'source': 'db', 'pattern_hits': 0, 'message_hits': 0}

        tokens = [token for token in normalized.split() if token]
        score_by_intent: Dict[str, float] = {}
        pattern_hits = 0
        message_hits = 0

        try:
            patterns = Pattern.objects.select_related('intent').order_by('-id')[:300]
            for pattern in patterns:
                intent_name = getattr(getattr(pattern, 'intent', None), 'name', None)
                if not intent_name:
                    continue
                pattern_text = normalize_chat_text(getattr(pattern, 'text', '') or '')
                if not pattern_text:
                    continue
                overlap = sum(1 for token in tokens if token in pattern_text)
                if overlap <= 0:
                    continue
                pattern_hits += 1
                score_by_intent[intent_name] = score_by_intent.get(intent_name, 0.0) + (0.18 * overlap)
        except Exception:
            pass

        try:
            recent_labels = MessageIntent.objects.select_related('intent', 'message').order_by('-id')[:250]
            for label in recent_labels:
                intent_name = getattr(getattr(label, 'intent', None), 'name', None)
                message = getattr(label, 'message', None)
                content = normalize_chat_text(getattr(message, 'content', '') or '')
                if not intent_name or not content:
                    continue
                overlap = sum(1 for token in tokens if token in content)
                if overlap <= 0:
                    continue
                message_hits += 1
                confidence = float(getattr(label, 'confidence', 0.5) or 0.5)
                score_by_intent[intent_name] = score_by_intent.get(intent_name, 0.0) + (0.12 * overlap * confidence)
        except Exception:
            pass

        if not score_by_intent:
            return None, 0.0, {'source': 'db', 'pattern_hits': pattern_hits, 'message_hits': message_hits}

        best_name, best_score = max(score_by_intent.items(), key=lambda item: item[1])
        intent = AIOrchestratorService._resolve_intent_record(best_name)
        confidence = max(0.0, min(0.92, round(best_score, 4)))
        return intent, confidence, {
            'source': 'db',
            'pattern_hits': pattern_hits,
            'message_hits': message_hits,
            'scores': score_by_intent,
        }

    @staticmethod
    def classify_intent(user_text: str) -> Tuple[Optional[Any], float]:
        normalized_text = normalize_chat_text(user_text)
        meal_plan_priority_terms = (
            'thuc don', 'thực đơn', 'meal plan', 'menu', 'lap thuc don', 'lập thực đơn',
            'tao thuc don', 'tạo thực đơn', 'len thuc don', 'lên thực đơn',
            'hom nay', 'hôm nay', 'ngay nay', 'ngày nay',
            'ngan sach', 'ngân sách', 'budget', '50k', '100k', 'chi phi', 'chi phí',
            'theo ngay', 'theo ngày', 'cho ngay', 'cho ngày', 'moi ngay', 'mỗi ngày',
        )
        meal_plan_action_terms = (
            'tao', 'tạo', 'lap', 'lập', 'len', 'lên', 'xay dung', 'xây dựng', 'goi y', 'gợi ý',
        )
        if normalized_text and any(term in normalized_text for term in meal_plan_priority_terms):
            if any(term in normalized_text for term in meal_plan_action_terms):
                meal_plan_intent = AIOrchestratorService._resolve_intent_record('meal_plan')
                if meal_plan_intent:
                    return meal_plan_intent, 0.95

        db_intent, db_confidence, _db_evidence = AIOrchestratorService._db_intent_signal(user_text)
        if db_intent and db_confidence >= 0.72:
            return db_intent, db_confidence

        try:
            local_llm_prediction = classify_intent_with_local_llm(user_text)
        except Exception:
            local_llm_prediction = None
        if local_llm_prediction:
            intent = AIOrchestratorService._resolve_intent_record(local_llm_prediction.get('intent'))
            if intent:
                return intent, float(local_llm_prediction.get('confidence') or 0.0)

        # 1. Thử dùng Embedding Similarity (TF-based)
        embedding_prediction = classify_intent_by_embedding(user_text)
        if embedding_prediction and embedding_prediction.intent_name:
            intent = AIOrchestratorService._resolve_intent_record(embedding_prediction.intent_name)
            if intent and embedding_prediction.confidence >= 0.7:
                return intent, embedding_prediction.confidence

        # 2. Thử dùng Smart Pattern Matching (Thuật toán mới)
        pattern_intent, pattern_conf = AIOrchestratorService._pattern_similarity_fallback(user_text)
        if pattern_intent:
            return pattern_intent, pattern_conf

        if db_intent and db_confidence >= 0.42:
            return db_intent, db_confidence

        # 3. Thử dùng Intent Model Prediction
        prediction = predict_intent(user_text)
        if prediction.intent_name:
            intent = AIOrchestratorService._resolve_intent_record(prediction.intent_name)
            if intent:
                return intent, prediction.confidence

        # 4. Fallback: lightweight local classifier
        try:
            label, conf, matches = local_classify_intent(user_text)
            if label and label != 'unknown':
                intent = AIOrchestratorService._resolve_intent_record(label)
                if intent:
                    return intent, float(conf)
        except Exception:
            pass

        # 5. Final fallback: keyword rules
        fallback_intent = AIOrchestratorService._keyword_fallback(user_text)
        if fallback_intent:
            return fallback_intent, 0.6

        return None, 0.0

    @staticmethod
    def _build_route_context(account, user_text: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        normalized = normalize_chat_text(user_text)
        route_context: Dict[str, Any] = {
            'cache_hit': False,
            'local_evidence': 0.0,
            'rag_density': 0.0,
            'candidate_count': len(candidates or []),
        }

        if normalized:
            try:
                route_context['cache_hit'] = ChatResponseCache.objects.filter(
                    normalized_query=normalized,
                ).exists()
            except Exception:
                pass

        if candidates:
            top_score = max((float(item.get('score', 0.0) or 0.0) for item in candidates), default=0.0)
            avg_score = sum(float(item.get('score', 0.0) or 0.0) for item in candidates) / max(1, len(candidates))
            route_context['local_evidence'] = round(min(1.0, (0.65 * top_score) + (0.35 * avg_score)), 4)

        try:
            rag_foods = semantic_search_with_scores(user_text, limit=5)
            route_context['rag_density'] = round(
                min(1.0, sum(float(item.get('similarity', 0.0) or 0.0) for item in rag_foods[:3])),
                4,
            )
        except Exception:
            pass

        return route_context

    @staticmethod
    def classify_intent_details(user_text: str) -> Dict[str, Any]:
        prediction = predict_intent(user_text)
        embedding_prediction = classify_intent_by_embedding(user_text)
        return {
            'top_intents': predict_top_intents(user_text),
            'prediction': prediction,
            'embedding_prediction': embedding_prediction,
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

    @staticmethod
    def log_search_event(account, user_text: str, result_count: int = 0, clicked_food=None):
        normalized_query = normalize_chat_text(user_text)
        kwargs = {
            'account': account,
            'query_text': user_text,
            'normalized_query': normalized_query,
            'result_count': result_count,
        }
        if clicked_food is not None:
            kwargs['clicked_food'] = clicked_food
            kwargs['clicked_food_stt'] = getattr(clicked_food, 'id', None)
        try:
            SearchEvent.objects.create(**kwargs)
        except Exception:
            pass

    @staticmethod
    def should_retrain_intent_model(stale_hours: int = 24) -> bool:
        try:
            latest = ModelMetadata.objects.filter(model_name='intent_classifier').order_by('-created_at').first()
        except Exception:
            # If the model metadata table is unavailable or DB access is disabled
            # (for example in isolated unit tests), treat the intent model as stale.
            return True
        if not latest:
            return True
        age_seconds = (django_timezone.now() - latest.created_at).total_seconds()
        return age_seconds >= stale_hours * 3600

    @staticmethod
    def trigger_retraining(force: bool = False) -> Dict[str, Any]:
        if force or AIOrchestratorService.should_retrain_intent_model():
            result = refresh_learning_from_feedback()
            result['model_status'] = train_intent_classifier(force=True)
            return result
        return get_intent_model_status()

    @staticmethod
    def _rank_local_candidates(account, user_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        try:
            foods = build_db_backed_candidate_pool(account, user_query=user_text, limit=max(top_k * 8, 40))
            safe_foods = filter_food_candidates(account, foods)
            return rank_food_candidates(account, safe_foods, limit=top_k, user_query=user_text)
        except Exception:
            return []

    @staticmethod
    def _rule_route(intent_name: Optional[str], candidates: List[Dict[str, Any]]) -> str:
        local_intents = {'recommendation', 'recipe', 'meal_plan'}
        if intent_name in local_intents and candidates:
            return 'local'
        return 'gemini' if GEMINI_ENABLED else 'local'

    @staticmethod
    def _resolve_ab_variant(account) -> Optional[Dict[str, Any]]:
        try:
            return ABTestingService.get_ai_route_variant(account)
        except Exception:
            return None

    @staticmethod
    def _choose_route_for_variant(
        variant_name: str,
        intent_name: Optional[str],
        confidence: float,
        safe_candidates: List[Dict[str, Any]],
        call_gemini: bool,
    ) -> Tuple[str, str]:
        if variant_name == 'local_rule':
            route = AIOrchestratorService._rule_route(intent_name, safe_candidates)
            return route, 'ab_local_rule'
        if variant_name == 'semantic_router':
            route = decide_route(float(confidence), safe_candidates, call_gemini, GEMINI_ENABLED)
            return route, 'ab_semantic_router'
        if variant_name == 'gemini_rag':
            return 'gemini', 'ab_gemini_rag'
        if variant_name == 'local_llm':
            return 'local', 'ab_local_llm'
        route = decide_route(float(confidence), safe_candidates, call_gemini, GEMINI_ENABLED)
        return route, 'default_router'

    @staticmethod
    def _has_viable_local_candidates(candidates: List[Dict[str, Any]], threshold: float = 0.4) -> bool:
        return bool(candidates and any(item.get('score', 0.0) >= threshold for item in candidates))

    @staticmethod
    def _build_rag_evidence(user_text: str, local_candidates: Optional[List[Dict[str, Any]]] = None, top_k: int = 5) -> Dict[str, Any]:
        evidence = {
            'foods': local_candidates or [],
            'recipes': [],
            'ingredients': [],
        }

        query = (user_text or '').strip()
        if not query:
            return evidence

        normalized_query = normalize_chat_text(query)

        try:
            from apps.nutrition.models import Recipe

            recipes = Recipe.objects.filter(
                Q(title__icontains=normalized_query)
                | Q(summary__icontains=normalized_query)
                | Q(instructions__icontains=normalized_query)
            ).order_by('-created_at')[:top_k]
            for recipe in recipes:
                evidence['recipes'].append({
                    'title': getattr(recipe, 'title', '') or '',
                    'summary': getattr(recipe, 'summary', '') or '',
                })
        except Exception:
            pass

        try:
            from apps.nutrition.models import Ingredient

            ingredients = Ingredient.objects.filter(name__icontains=normalized_query).order_by('name')[:top_k]
            evidence['ingredients'] = [
                getattr(ingredient, 'name', '') for ingredient in ingredients if getattr(ingredient, 'name', None)
            ]
        except Exception:
            pass

        if not evidence['foods']:
            try:
                scored_foods = semantic_search_with_scores(query, limit=top_k)
                evidence['foods'] = [
                    {
                        'food': item.get('food'),
                        'score': float(item.get('similarity', 0.0)),
                        'reasons': ['Semantic DB match'],
                    }
                    for item in scored_foods
                ]
            except Exception:
                pass

        return evidence

    @staticmethod
    def orchestrate(user_text: str, account=None, chat_session=None, call_gemini: bool = False, top_k: int = 5) -> Dict[str, Any]:
        """Decide whether to serve local DB results or fallback to Gemini.

        Returns a dict with keys: `path` ('local'|'gemini'), `intent_name`,
        `intent_confidence`, and `candidates`, `personalization_context`, and
        `rag_evidence` when Gemini is chosen.
        """
        intent, confidence = AIOrchestratorService.classify_intent(user_text)
        intent_name = getattr(intent, 'name', None) if intent else None
        personalization_context = get_personalization_context(account)

        result: Dict[str, Any] = {
            'intent_name': intent_name,
            'intent_confidence': float(confidence),
            'personalization_context': personalization_context,
            'intent_model_stale': AIOrchestratorService.should_retrain_intent_model(),
        }

        local_intents = ('recommendation', 'recipe', 'meal_plan')
        local_candidates: List[Dict[str, Any]] = []

        if intent_name in local_intents or intent_name is None:
            local_candidates = AIOrchestratorService._rank_local_candidates(account, user_text, top_k=top_k)

        # Apply policy checks to remove unsafe candidates before routing
        policy = evaluate_policies(account, local_candidates, user_text)
        safe_candidates = policy.get('safe_candidates', local_candidates)
        route_context = AIOrchestratorService._build_route_context(account, user_text, safe_candidates)

        ab_assignment = AIOrchestratorService._resolve_ab_variant(account)
        ab_variant = ab_assignment.get('variant_name') if ab_assignment else None
        route, decision = AIOrchestratorService._choose_route_for_variant(
            ab_variant or 'semantic_router',
            intent_name,
            float(confidence),
            safe_candidates,
            call_gemini,
        )
        if not ab_variant:
            route = decide_route(
                float(confidence),
                safe_candidates,
                call_gemini,
                GEMINI_ENABLED,
                route_context=route_context,
            )
            decision = 'db_router_policy'

        result.update({
            'ab_experiment': ab_assignment,
            'ab_variant': ab_variant,
            'route_context': route_context,
        })

        if account and ab_variant:
            try:
                ABTestingService.record_ai_route_event(
                    account,
                    event_type='recommendation_shown',
                    variant_name=ab_variant,
                    value=max((item.get('score', 0.0) for item in safe_candidates), default=0.0),
                    metadata={
                        'source': 'ai_orchestrator',
                        'route': route,
                        'decision': decision,
                        'intent_name': intent_name,
                        'intent_confidence': float(confidence),
                        'candidate_count': len(safe_candidates),
                        'policy_issues': policy.get('issues', []),
                    },
                )
            except Exception:
                pass

        if route == 'local':
            result.update({
                'path': 'local',
                'candidates': safe_candidates,
                'decision': decision,
                'policy_issues': policy.get('issues', []),
            })
            return result

        # route == 'gemini'
        rag_evidence = AIOrchestratorService._build_rag_evidence(user_text, local_candidates=safe_candidates, top_k=top_k)
        result.update({
            'path': 'gemini',
            'candidates': safe_candidates,
            'rag_evidence': rag_evidence,
            'decision': decision,
            'policy_issues': policy.get('issues', []),
        })
        return result


__all__ = [
    'AIOrchestratorService',
    'build_user_preference_profile',
    'get_personalization_context',
    'rank_food_candidates',
    'score_food_for_user',
    'summarize_ai_activity',
]
